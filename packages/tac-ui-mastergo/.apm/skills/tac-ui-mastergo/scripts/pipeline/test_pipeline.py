import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).resolve().parent / "pipeline.py"
SPEC = importlib.util.spec_from_file_location("pipeline", SCRIPT_PATH)
pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(pipeline)


class PipelineRegistryPreparationTest(unittest.TestCase):
    def test_prepare_widget_registry_keeps_explicit_snapshot_compatibility(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_path = Path(temp_dir) / "snapshot.json"
            snapshot_path.write_text(json.dumps({"widgets": []}), encoding="utf-8")

            registry_path, meta = pipeline._prepare_widget_registry(
                output_dir=temp_dir,
                widget_root="unused",
                widget_registry_snapshot=str(snapshot_path),
                rebuild_widget_registry=False,
            )

            self.assertEqual(str(snapshot_path.resolve()), registry_path)
            self.assertEqual("snapshot", meta["source"])

    def test_prepare_widget_registry_uses_provider_and_copies_active_snapshot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            library_dir = root / "references" / "libraries" / "caui"
            library_dir.mkdir(parents=True)
            library_snapshot = library_dir / "widget_registry.snapshot.json"
            library_snapshot.write_text(
                json.dumps({"meta": {"libraryId": "caui"}, "widgets": []}),
                encoding="utf-8",
            )
            provider = {
                "libraryId": "caui",
                "snapshotFile": "widget_registry.snapshot.json",
                "_providerPath": str(library_dir / "provider.json"),
            }
            active_snapshot = root / "references" / "widget_registry.snapshot.json"

            with patch.object(pipeline, "DEFAULT_WIDGET_REGISTRY_SNAPSHOT", active_snapshot):
                with patch("build_widget_registry._load_provider", return_value=provider) as load_provider:
                    with patch("build_widget_registry._provider_dir", return_value=library_dir):
                        with patch(
                            "build_widget_registry.build_registry_for_provider",
                            return_value={"meta": {"libraryId": "caui"}},
                        ) as build_registry:
                            registry_path, meta = pipeline._prepare_widget_registry(
                                output_dir=temp_dir,
                                widget_root="unused",
                                library="caui",
                                project_root=root,
                            )

            load_provider.assert_called_once_with("caui")
            build_registry.assert_called_once_with(provider, root, refresh=False)
            self.assertEqual(str(active_snapshot.resolve()), registry_path)
            self.assertEqual("provider", meta["source"])
            self.assertEqual("caui", meta["libraryId"])
            self.assertEqual(
                json.loads(library_snapshot.read_text(encoding="utf-8")),
                json.loads(active_snapshot.read_text(encoding="utf-8")),
            )

    def test_prepare_widget_registry_uses_active_library_when_library_not_set(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            library_dir = root / "references" / "libraries" / "caui"
            library_dir.mkdir(parents=True)
            (library_dir / "widget_registry.snapshot.json").write_text(
                json.dumps({"meta": {"libraryId": "caui"}, "widgets": []}),
                encoding="utf-8",
            )
            provider = {
                "libraryId": "caui",
                "snapshotFile": "widget_registry.snapshot.json",
                "_providerPath": str(library_dir / "provider.json"),
            }

            with patch.object(
                pipeline,
                "DEFAULT_WIDGET_REGISTRY_SNAPSHOT",
                root / "references" / "widget_registry.snapshot.json",
            ):
                with patch("build_widget_registry._load_provider", return_value=provider) as load_provider:
                    with patch("build_widget_registry._provider_dir", return_value=library_dir):
                        with patch(
                            "build_widget_registry.build_registry_for_provider",
                            return_value={"meta": {"libraryId": "caui"}},
                        ):
                            _, meta = pipeline._prepare_widget_registry(
                                output_dir=temp_dir,
                                widget_root="unused",
                                project_root=root,
                            )

            load_provider.assert_called_once_with(None)
            self.assertEqual("provider", meta["source"])
            self.assertEqual("caui", meta["libraryId"])


if __name__ == "__main__":
    unittest.main()
