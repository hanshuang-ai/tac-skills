import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parent / "extract_semantic_mapping.py"
SPEC = importlib.util.spec_from_file_location("extract_semantic_mapping", SCRIPT_PATH)
extract_semantic_mapping = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(extract_semantic_mapping)


def _write_json(path: Path, content: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")


class ExtractSemanticMappingTest(unittest.TestCase):
    def test_text_style_matcher_supports_registry_meta_patterns(self):
        extract_family, is_library_style = extract_semantic_mapping._create_text_style_matcher(
            [
                r"^(CAUITextStyle[A-Za-z0-9]+?)([RB])?$",
                r"^(CAUI\.TextAppearance\.[A-Za-z0-9_.]+?)$",
            ],
            ["CAUITextStyle", "CAUI.TextAppearance"],
        )

        self.assertEqual(("CAUITextStyleTitle", "B"), extract_family("CAUITextStyleTitleB"))
        self.assertEqual(
            ("CAUI.TextAppearance.Title", None),
            extract_family("CAUI.TextAppearance.Title"),
        )
        self.assertTrue(is_library_style("CAUI.TextAppearance.Title"))
        self.assertFalse(is_library_style("WTTextStyleTitle"))

    def test_extract_semantic_mapping_uses_registry_meta_for_caui_text_attrs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_path = root / "input.json"
            registry_path = root / "registry.json"
            output_path = root / "semantic_mapping.json"

            _write_json(
                input_path,
                {
                    "dsl": {
                        "styles": {
                            "font_1": {
                                "value": {
                                    "family": "CAUIRegular",
                                    "size": 24,
                                    "lineHeight": "32",
                                },
                                "token": "font/CAUI.TextAppearance.Title",
                            },
                            "paint_1": {
                                "value": ["#FFFFFF"],
                                "token": "color/caui_title",
                            },
                        },
                        "nodes": [
                            {
                                "id": "button",
                                "type": "INSTANCE",
                                "componentInfo": {"description": "CAUIButton"},
                                "children": [
                                    {
                                        "id": "label",
                                        "type": "TEXT",
                                        "name": "label style:CAUI.TextAppearance.Title #color:caui_title",
                                        "text": [{"text": "OK", "font": "font_1"}],
                                        "textColor": [{"color": "paint_1"}],
                                    }
                                ],
                            }
                        ],
                    }
                },
            )
            _write_json(
                registry_path,
                {
                    "meta": {
                        "textStylePatterns": [r"^(CAUI\.TextAppearance\.[A-Za-z0-9_.]+?)$"],
                        "textStylePrefixes": ["CAUI.TextAppearance"],
                        "preferredTextAttrs": ["cauiTextStyle", "android:textAppearance"],
                        "preferredColorAttrs": ["android:textColor"],
                    },
                    "widgets": [
                        {
                            "simpleName": "CAUIButton",
                            "className": "com.incall.apps.caui.widget.CAUIButton",
                            "styleableName": "CAUIButton",
                            "aliases": ["CAUIButton"],
                            "variants": [],
                            "xmlAttrs": ["cauiTextStyle", "android:textColor"],
                            "textStyleAttrs": ["cauiTextStyle", "android:textAppearance"],
                            "textColorAttrs": ["android:textColor"],
                        }
                    ],
                    "textStyles": [
                        {
                            "name": "CAUI.TextAppearance.Title",
                            "normalized": "cauitextappearancetitle",
                            "family": "CAUI.TextAppearance.Title",
                            "familyNormalized": "cauitextappearancetitle",
                            "styleRef": "@style/CAUI.TextAppearance.Title",
                        }
                    ],
                    "colorResources": [
                        {
                            "name": "caui_title",
                            "normalized": "cauititle",
                        }
                    ],
                },
            )

            result = extract_semantic_mapping.extract_semantic_mapping(
                str(input_path),
                str(registry_path),
                str(output_path),
            )

            label = next(item for item in result["nodes"] if item["nodeId"] == "label")
            self.assertEqual("@style/CAUI.TextAppearance.Title", label["text"]["styleRef"])
            self.assertEqual("cauiTextStyle", label["text"]["ownership"]["preferredAttr"])
            self.assertEqual("@color/caui_title", label["text"]["color"]["ref"])
            self.assertEqual("android:textColor", label["text"]["color"]["ownership"]["preferredAttr"])

    def test_node_name_only_widget_signal_does_not_resolve_widget(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_path = root / "input.json"
            registry_path = root / "registry.json"
            output_path = root / "semantic_mapping.json"

            _write_json(
                input_path,
                {
                    "dsl": {
                        "styles": {},
                        "nodes": [
                            {
                                "id": "button",
                                "type": "INSTANCE",
                                "name": "WTButton",
                            }
                        ],
                    }
                },
            )
            _write_json(
                registry_path,
                {
                    "widgets": [
                        {
                            "simpleName": "WTButton",
                            "className": "wtcl.lib.widget.WTButton",
                            "styleableName": "WTButton",
                            "aliases": ["WTButton"],
                            "variants": [],
                            "xmlAttrs": [],
                        }
                    ],
                    "textStyles": [],
                    "colorResources": [],
                },
            )

            result = extract_semantic_mapping.extract_semantic_mapping(
                str(input_path),
                str(registry_path),
                str(output_path),
            )

            self.assertEqual([], result["nodes"])

    def test_node_with_only_unresolved_errors_is_skipped(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_path = root / "input.json"
            registry_path = root / "registry.json"
            output_path = root / "semantic_mapping.json"

            _write_json(
                input_path,
                {
                    "dsl": {
                        "styles": {},
                        "nodes": [
                            {
                                "id": "unresolved_node",
                                "type": "INSTANCE",
                                "componentId": "some_master_id",
                            }
                        ],
                    }
                },
            )
            _write_json(
                registry_path,
                {
                    "widgets": [],
                    "textStyles": [],
                    "colorResources": [],
                },
            )

            result = extract_semantic_mapping.extract_semantic_mapping(
                str(input_path),
                str(registry_path),
                str(output_path),
            )

            self.assertEqual([], result["nodes"])


if __name__ == "__main__":
    unittest.main()
