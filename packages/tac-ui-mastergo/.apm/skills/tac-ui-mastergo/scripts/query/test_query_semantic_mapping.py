import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

# Dynamically load query_semantic_mapping.py
SCRIPT_PATH = Path(__file__).resolve().parent / "query_semantic_mapping.py"
SPEC = importlib.util.spec_from_file_location("query_semantic_mapping", SCRIPT_PATH)
query_semantic_mapping = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
import sys
sys.modules[SPEC.name] = query_semantic_mapping
SPEC.loader.exec_module(query_semantic_mapping)


class QuerySemanticMappingTest(unittest.TestCase):
    def _write_fixture(self, temp_dir: Path) -> Path:
        payload = {
            "meta": {
                "source": "dummy_raw.json",
                "nodeCount": 2
            },
            "nodes": [
                {
                    "nodeId": "1:10",
                    "nodeType": "TEXT",
                    "evidence": ["TEXT.textColor[]"],
                    "unresolved": [],
                    "text": {
                        "rawText": "Hello World",
                        "font": {
                            "fontFamily": "AlibabaPuHuiTiR",
                            "fontSize": 32
                        },
                        "colorToken": "wt_primary_color",
                        "colorValue": "#FF0000"
                    }
                },
                {
                    "nodeId": "1:11",
                    "nodeType": "LAYER",
                    "evidence": ["styles.token"],
                    "unresolved": ["missing color resource"],
                    "resources": {
                        "fillColorValue": "#00FF00",
                        "fillColorToken": "wt_secondary_color"
                    }
                }
            ]
        }
        path = temp_dir / "semantic_mapping.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_load_semantic_mapping_and_build_index(self):
        with tempfile.TemporaryDirectory() as td:
            mapping_path = self._write_fixture(Path(td))
            mapping_data = query_semantic_mapping.load_semantic_mapping(mapping_path)
            index = query_semantic_mapping.build_node_index(mapping_data)

            self.assertEqual(len(index), 2)
            self.assertIn("1:10", index)
            self.assertIn("1:11", index)
            self.assertEqual(index["1:10"]["nodeType"], "TEXT")
            self.assertEqual(index["1:11"]["resources"]["fillColorValue"], "#00FF00")

    def test_format_text_summary(self):
        with tempfile.TemporaryDirectory() as td:
            mapping_path = self._write_fixture(Path(td))
            mapping_data = query_semantic_mapping.load_semantic_mapping(mapping_path)
            index = query_semantic_mapping.build_node_index(mapping_data)

            # Format existing node
            summary_found = query_semantic_mapping.format_text_summary("1:10", index["1:10"])
            self.assertIn("Node ID: 1:10 (TEXT)", summary_found)
            self.assertIn("Raw Text: \"Hello World\"", summary_found)
            self.assertIn("Color: #FF0000 (Token: wt_primary_color)", summary_found)

            # Format missing node
            summary_missing = query_semantic_mapping.format_text_summary("1:99", None)
            self.assertIn("Node ID: 1:99", summary_missing)
            self.assertIn("[NOT FOUND in semantic mapping]", summary_missing)


if __name__ == "__main__":
    unittest.main()
