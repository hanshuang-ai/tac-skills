import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parent / "build_widget_registry.py"
SPEC = importlib.util.spec_from_file_location("build_widget_registry", SCRIPT_PATH)
build_widget_registry = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(build_widget_registry)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_aar(root: Path, name: str = "caui-1.0.0") -> Path:
    aar_root = root / ".gradle" / "caches" / "transforms-4" / "hash" / "transformed" / name
    _write_text(aar_root / "AndroidManifest.xml", "<manifest />")
    _write_text(
        aar_root / "res" / "values" / "values.xml",
        """<resources>
    <declare-styleable name="CAUIButton">
        <attr name="cauiButtonType">
            <enum name="primary" value="0" />
            <enum name="secondary" value="1" />
        </attr>
        <attr name="android:textColor" />
    </declare-styleable>
    <declare-styleable name="AppCompatNoise">
        <attr name="noiseAttr" />
    </declare-styleable>
    <style name="CAUI.TextAppearance.Title">
        <item name="android:textSize">24sp</item>
        <item name="android:textColor">@color/caui_title</item>
    </style>
    <color name="caui_title">#FFFFFF</color>
</resources>""",
    )
    jar_path = aar_root / "jars" / "classes.jar"
    jar_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(jar_path, "w") as jar:
        jar.writestr("com/incall/apps/caui/widget/CAUIButton.class", b"")
        jar.writestr("com/incall/apps/caui/widget/CAUIButton$Inner.class", b"")
        jar.writestr("androidx/appcompat/AppCompatNoise.class", b"")
    return aar_root


class BuildWidgetRegistryTest(unittest.TestCase):
    def test_build_class_index_from_jar_skips_inner_classes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            aar_root = _make_aar(Path(temp_dir))

            index = build_widget_registry._build_class_index_from_jar(
                aar_root / "jars" / "classes.jar"
            )

            self.assertEqual(
                "com.incall.apps.caui.widget.CAUIButton",
                index["CAUIButton"],
            )
            self.assertNotIn("CAUIButton$Inner", index)

    def test_discover_aar_path_finds_extracted_gradle_transform(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            aar_root = _make_aar(root, "caui-3.0.9.3.2-SNAPSHOT")

            found = build_widget_registry._discover_aar_path(
                root,
                "com.incall.apps",
                "caui",
                "3.0.9.3.2-SNAPSHOT",
            )

            self.assertEqual(aar_root, found)

    def test_styleable_filter_supports_prefix_and_class_index_modes(self):
        prefix_filter = build_widget_registry._create_styleable_filter(
            {"mode": "prefix", "prefixes": ["WT"], "excludeSuffixes": ["Style"]},
            {},
        )
        self.assertTrue(prefix_filter("WTButton"))
        self.assertFalse(prefix_filter("WTButtonStyle"))
        self.assertFalse(prefix_filter("CAUIButton"))

        class_index_filter = build_widget_registry._create_styleable_filter(
            {
                "mode": "class_index",
                "excludePrefixes": ["androidx"],
                "excludeSuffixes": ["Style"],
            },
            {
                "CAUIButton": "com.incall.apps.caui.widget.CAUIButton",
                "AppCompatNoise": "androidx.appcompat.AppCompatNoise",
            },
        )
        self.assertTrue(class_index_filter("CAUIButton"))
        self.assertFalse(class_index_filter("MissingButton"))
        self.assertFalse(class_index_filter("AppCompatNoise"))

    def test_build_registry_for_provider_uses_aar_class_index_and_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            aar_root = _make_aar(root, "caui-3.0.9.3.2-SNAPSHOT")
            library_dir = root / "references" / "libraries" / "caui"
            _write_text(
                library_dir / "widget_semantic_rules.json",
                json.dumps(
                    {
                        "widget_overrides": {
                            "CAUIButton": {
                                "aliases": ["主按钮"],
                                "variantAttr": "cauiButtonType",
                            }
                        },
                        "manual_widgets": [],
                    },
                    ensure_ascii=False,
                ),
            )
            provider = {
                "libraryId": "caui",
                "aarDependency": {
                    "group": "com.incall.apps",
                    "artifact": "caui",
                    "version": "3.0.9.3.2-SNAPSHOT",
                },
                "defaultPackage": "com.incall.apps.caui.widget",
                "styleableFilter": {
                    "mode": "class_index",
                    "excludePrefixes": ["androidx"],
                    "excludeSuffixes": ["Style"],
                },
                "textStylePatterns": ["^(CAUI\\.TextAppearance\\.[A-Za-z0-9_.]+?)$"],
                "textStylePrefixes": ["CAUI.TextAppearance"],
                "preferredTextAttrs": ["android:textAppearance"],
                "preferredColorAttrs": ["android:textColor"],
                "rulesFile": "widget_semantic_rules.json",
                "snapshotFile": "widget_registry.snapshot.json",
                "_providerPath": str(library_dir / "provider.json"),
            }

            registry = build_widget_registry.build_registry_for_provider(
                provider,
                root,
                refresh=True,
            )
            cached = build_widget_registry.build_registry_for_provider(
                provider,
                root,
                refresh=False,
            )

            widget = registry["widgets"][0]
            self.assertEqual("CAUIButton", widget["simpleName"])
            self.assertEqual("com.incall.apps.caui.widget.CAUIButton", widget["className"])
            self.assertEqual(["primary", "secondary"], [item["name"] for item in widget["variants"]])
            self.assertEqual("caui", registry["meta"]["libraryId"])
            self.assertEqual(str(aar_root), registry["meta"]["aarSourcePath"])
            self.assertEqual(["android:textColor"], registry["meta"]["preferredColorAttrs"])
            self.assertEqual(1, registry["meta"]["widgetCount"])
            self.assertEqual(registry, cached)


if __name__ == "__main__":
    unittest.main()
