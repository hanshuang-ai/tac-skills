import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parent / "dsl_query.py"
SPEC = importlib.util.spec_from_file_location("dsl_query", SCRIPT_PATH)
dsl_query = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
import sys
sys.modules[SPEC.name] = dsl_query
SPEC.loader.exec_module(dsl_query)


class DslQueryTest(unittest.TestCase):
    def _write_fixture(self, root: Path) -> Path:
        payload = {
            "dsl": {
                "styles": {
                    "paint_bg": {"value": ["#FFFFFF"], "token": "Color/Bg"},
                    "paint_img": {"value": [{"url": "https://example.invalid/huge.png"}], "token": "Image/Hero"},
                    "font_title": {
                        "value": {
                            "family": "AlibabaPuHuiTiR",
                            "size": 28,
                            "lineHeight": "40",
                            "letterSpacing": "auto",
                        },
                        "token": "WTTextStyleBody2R",
                    },
                },
                "nodes": [
                    {
                        "id": "1:1",
                        "name": "root",
                        "type": "FRAME",
                        "layoutStyle": {"relativeX": 0, "relativeY": 0, "width": 200, "height": 100},
                        "children": [
                            {
                                "id": "1:2",
                                "name": "image",
                                "type": "LAYER",
                                "fill": "paint_img",
                                "layoutStyle": {"relativeX": 10, "relativeY": 20, "width": 50, "height": 40},
                            },
                            {
                                "id": "1:3",
                                "name": "title",
                                "type": "TEXT",
                                "layoutStyle": {"relativeX": 70, "relativeY": 20, "width": 80, "height": 40},
                                "text": [{"text": "Hello", "font": "font_title"}],
                                "textColor": [{"color": "paint_bg"}],
                            },
                        ],
                    }
                ],
            }
        }
        path = root / "mastergo_raw.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_node_query_is_depth_limited_and_omits_urls_by_default(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write_fixture(Path(td))
            index, styles, warnings = dsl_query._load_sources([str(path)])
            self.assertFalse(warnings)
            payload = dsl_query._node_summary(
                index["1:1"],
                index,
                styles,
                depth=1,
                max_children=1,
                max_text=20,
                max_name=20,
                include_urls=False,
                include_path_data=False,
                path_data_limit=40,
                fields={"geometry", "styles", "text", "path", "children"},
            )
            self.assertEqual(2, payload["children"]["count"])
            self.assertTrue(payload["children"]["truncated"])
            self.assertEqual(1, len(payload["children"]["items"]))
            child = payload["children"]["items"][0]
            self.assertEqual({"x": 10.0, "y": 20.0, "width": 50.0, "height": 40.0}, child["bounds"]["parent_relative"])
            self.assertEqual({"x": 10.0, "y": 20.0, "width": 50.0, "height": 40.0}, child["bounds"]["raw"])
            self.assertEqual("[URL_OMITTED]", child["styles"]["fill"]["value"])

    def test_find_returns_compact_limited_results(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write_fixture(Path(td))
            index, _styles, _warnings = dsl_query._load_sources([str(path)])
            matches = [
                dsl_query._compact_record(record, max_name=20)
                for record in index.values()
                if record.node.get("type") == "TEXT"
            ]
            self.assertEqual(1, len(matches))
            self.assertEqual("1:3", matches[0]["id"])
            self.assertEqual({"x": 70.0, "y": 20.0, "width": 80.0, "height": 40.0}, matches[0]["bounds"]["parent_relative"])


if __name__ == "__main__":
    unittest.main()
