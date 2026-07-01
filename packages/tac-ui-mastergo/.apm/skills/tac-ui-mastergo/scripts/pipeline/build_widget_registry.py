#!/usr/bin/env python3
"""
build_widget_registry.py -- Build a minimal widget registry from WT02_Widget.

The registry is intentionally small. It captures only what Mode B needs to
select a widget, write XML attrs, and reuse existing text/color resources.
"""

import argparse
import json
import os
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


ANDROID_NS = "{http://schemas.android.com/apk/res/android}"
DEFAULT_WIDGET_ROOT = r"D:\code\WT02_Widget"
DEFAULT_SNAPSHOT_PATH = Path(__file__).resolve().parent.parent.parent / "references" / "widget_registry.snapshot.json"
DEFAULT_REFERENCES_DIR = Path(__file__).resolve().parent.parent.parent / "references"


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def _local_name(tag: str) -> str:
    if not tag:
        return ""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _load_rules(script_dir: Path, rules_path: str | None) -> dict:
    if rules_path:
        path = Path(rules_path)
    else:
        path = script_dir.parent.parent / "references" / "widget_semantic_rules.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _parse_attrs(attrs_path: Path) -> dict[str, dict]:
    tree = ET.parse(attrs_path)
    root = tree.getroot()
    styleables: dict[str, dict] = {}
    for elem in root.findall("declare-styleable"):
        name = elem.get("name")
        if not name:
            continue
        entry = {"attrs": [], "enums": {}}
        for child in elem.findall("attr"):
            attr_name = child.get("name")
            if not attr_name:
                continue
            entry["attrs"].append(attr_name)
            enum_names = [
                enum_elem.get("name")
                for enum_elem in child.findall("enum")
                if enum_elem.get("name")
            ]
            if enum_names:
                entry["enums"][attr_name] = enum_names
        styleables[name] = entry
    return styleables


def _safe_parse_xml(path: Path):
    try:
        return ET.parse(path)
    except ET.ParseError:
        return None


def _build_class_index_from_jar(jar_path: Path) -> dict[str, str]:
    if not jar_path.exists():
        return {}

    class_index: dict[str, str] = {}
    with zipfile.ZipFile(jar_path, "r") as jar:
        for name in jar.namelist():
            if not name.endswith(".class") or "$" in name:
                continue
            fqcn = name.removesuffix(".class").replace("/", ".")
            simple_name = fqcn.rsplit(".", 1)[-1]
            class_index[simple_name] = fqcn
    return class_index


def _build_class_index_from_aar(aar_path: Path) -> dict[str, str]:
    for jar_path in (aar_path / "jars" / "classes.jar", aar_path / "classes.jar"):
        if jar_path.exists():
            return _build_class_index_from_jar(jar_path)
    return {}


def _is_extracted_aar(path: Path) -> bool:
    return (
        path.is_dir()
        and (path / "AndroidManifest.xml").exists()
        and (path / "res" / "values" / "values.xml").exists()
    )


def _discover_aar_path(project_root: Path, group: str, artifact: str, version: str) -> Path | None:
    if version:
        name_patterns = [f"{artifact}-{version}*", f"{artifact.lower()}-{version}*"]
    else:
        name_patterns = [f"{artifact}-*", f"{artifact.lower()}-*"]

    search_roots = [
        project_root / ".gradle" / "caches",
        project_root / ".gradle",
        Path.home() / ".gradle" / "caches",
    ]
    for search_root in search_roots:
        if not search_root.exists():
            continue
        transform_roots = list(search_root.glob("transforms-*"))
        roots = transform_roots or [search_root]
        matches: list[Path] = []
        for root in roots:
            for pattern in name_patterns:
                candidates = [
                    *root.glob(f"*/transformed/{pattern}"),
                    *root.glob(f"transformed/{pattern}"),
                    *root.glob(pattern),
                ]
                matches.extend(path for path in candidates if _is_extracted_aar(path))
        if matches:
            matches.sort(key=lambda path: path.stat().st_mtime, reverse=True)
            return matches[0]
    return None


def _iter_value_xml_paths(root: Path) -> tuple[list[Path], bool]:
    if _is_extracted_aar(root):
        return sorted((root / "res" / "values").glob("*.xml")), True
    return sorted(root.glob("app/src/**/*.xml")), False


def _matches_text_style_pattern(style_name: str, patterns: list[str]) -> tuple[str, str | None] | None:
    for pattern in patterns:
        match = re.match(pattern, style_name)
        if not match:
            continue
        variant = match.group(2) if match.lastindex and match.lastindex >= 2 else None
        return match.group(1), variant
    return None


def _parse_style_catalog(
    widget_root: Path,
    text_style_patterns: list[str] | None = None,
    text_style_prefixes: list[str] | None = None,
) -> tuple[dict[str, dict], list[dict], list[dict]]:
    style_catalog: dict[str, dict] = {}
    text_styles: dict[str, dict] = {}
    color_resources: dict[str, dict] = {}
    value_paths, is_aar = _iter_value_xml_paths(widget_root)

    for path in value_paths:
        tree = _safe_parse_xml(path)
        if not tree:
            continue
        root = tree.getroot()
        for style_elem in root.findall("style"):
            style_name = style_elem.get("name")
            if not style_name:
                continue
            items = {}
            for item in style_elem.findall("item"):
                item_name = item.get("name")
                if item_name:
                    items[item_name] = (item.text or "").strip()
            style_catalog.setdefault(
                style_name,
                {
                    "name": style_name,
                    "path": str(path),
                    "items": items,
                },
            )
            if _is_text_style(style_name, items, text_style_patterns, text_style_prefixes):
                text_styles.setdefault(
                    style_name,
                    _build_text_style_entry(style_name, items, text_style_patterns),
                )

        if not is_aar and path.name != "colors.xml":
            continue
        for child in root:
            if _local_name(child.tag) != "color":
                continue
            resource_name = child.get("name")
            if not resource_name:
                continue
            color_resources.setdefault(
                resource_name,
                {
                    "name": resource_name,
                    "normalized": _normalize(resource_name),
                    "path": str(path),
                },
            )

    return style_catalog, list(text_styles.values()), list(color_resources.values())


def _create_styleable_filter(filter_config: dict | None, class_index: dict[str, str]):
    config = filter_config or {}
    mode = config.get("mode", "prefix")
    excluded_suffixes = tuple(config.get("excludeSuffixes", []))
    excluded_prefixes = tuple(config.get("excludePrefixes", []))

    def is_excluded(name: str) -> bool:
        fqcn = class_index.get(name, "")
        return (
            any(name.endswith(suffix) for suffix in excluded_suffixes)
            or any(name.startswith(prefix) or fqcn.startswith(f"{prefix}.") for prefix in excluded_prefixes)
        )

    if mode == "class_index":
        return lambda name: name in class_index and not is_excluded(name)

    prefixes = tuple(config.get("prefixes", ["WT", "Wt"]))
    return lambda name: name.startswith(prefixes) and not is_excluded(name)


def _is_widget_styleable(name: str) -> bool:
    return _create_styleable_filter(
        {"mode": "prefix", "prefixes": ["WT", "Wt"], "excludeSuffixes": ["Style", "DefaultAdapter", "Adapter"]},
        {},
    )(name)


def _is_text_style(
    style_name: str,
    items: dict[str, str],
    text_style_patterns: list[str] | None = None,
    text_style_prefixes: list[str] | None = None,
) -> bool:
    if _matches_text_style_pattern(style_name, text_style_patterns or []):
        return True
    if any(style_name.startswith(prefix) for prefix in (text_style_prefixes or ["WTTextStyle"])):
        return True

    text_item_patterns = (
        "android:textSize",
        "android:textColor",
        "wtTextSize",
        "wtTextColor",
        "wtSubTextSize",
        "wtSubTextColor",
        "wtItemTextSize",
        "wtItemTextColor",
        "wtDataTextSize",
        "wtDataTextColor",
        "wtSelectTextSize",
        "wtSelectTextStyle",
        "wtDefaultTextStyle",
        "wtEtTextSize",
        "wtBtnTextSize",
        "wtInputEtTextSize",
        "wtInputBtnTextSize",
    )
    if any(pattern in item_name for item_name in items for pattern in text_item_patterns):
        return True

    normalized_name = _normalize(style_name)
    keyword_hits = (
        "textstyle",
        "textpicker",
        "pickerviewstyle",
        "titletextstyle",
        "daytextstyle",
        "bubbletextstyle",
        "radiobuttonstyle",
    )
    return any(keyword in normalized_name for keyword in keyword_hits)


def _extract_text_style_family(
    style_name: str,
    text_style_patterns: list[str] | None = None,
) -> tuple[str, str | None]:
    matched = _matches_text_style_pattern(
        style_name,
        text_style_patterns or [r"^(WTTextStyle[A-Za-z0-9]+?)([RB])?$"],
    )
    if not matched:
        return style_name, None
    return matched


def _build_text_style_entry(
    style_name: str,
    items: dict[str, str],
    text_style_patterns: list[str] | None = None,
) -> dict:
    family, variant = _extract_text_style_family(style_name, text_style_patterns)
    text_style = (items.get("android:textStyle") or "").strip().lower()
    if variant == "B" or "bold" in text_style:
        weight = "bold"
    elif variant == "R" or text_style:
        weight = "normal"
    else:
        weight = None

    metrics = {}
    metric_items = (
        ("android:textSize", "textSize"),
        ("android:lineSpacingExtra", "lineSpacingExtra"),
        ("android:letterSpacing", "letterSpacing"),
        ("android:fontFamily", "fontFamily"),
        ("android:textColor", "textColor"),
    )
    for item_name, output_name in metric_items:
        value = (items.get(item_name) or "").strip()
        if value:
            metrics[output_name] = value

    return {
        "name": style_name,
        "normalized": _normalize(style_name),
        "styleRef": f"@style/{style_name}",
        "family": family,
        "familyNormalized": _normalize(family),
        "variant": variant,
        "weight": weight,
        "metrics": metrics,
    }


def _extract_text_style_attrs(attr_names: list[str]) -> list[str]:
    return sorted(attr_name for attr_name in attr_names if "textstyle" in _normalize(attr_name))


def _extract_text_color_attrs(attr_names: list[str]) -> list[str]:
    return sorted(attr_name for attr_name in attr_names if "textcolor" in _normalize(attr_name))


def _build_widget_entry(
    styleable_name: str,
    styleable_entry: dict,
    overrides: dict,
    style_catalog: dict[str, dict],
    class_index: dict[str, str] | None = None,
    default_package: str = "wtcl.lib.widget",
) -> dict:
    simple_name = overrides.get("simpleName", styleable_name)
    class_index = class_index or {}
    class_name = overrides.get("className") or class_index.get(simple_name) or f"{default_package}.{simple_name}"
    aliases = [simple_name, styleable_name]
    aliases.extend(overrides.get("aliases", []))
    aliases = sorted({alias for alias in aliases if alias})

    variant_attr = overrides.get("variantAttr")
    if not variant_attr and styleable_entry["enums"]:
        variant_attr = next(iter(styleable_entry["enums"]))
    variant_values = styleable_entry["enums"].get(variant_attr, []) if variant_attr else []

    variants = []
    style_map = overrides.get("variantStyleMap", {})
    for value in variant_values:
        style_refs = [style_name for style_name in style_map.get(value, []) if style_name in style_catalog]
        variants.append(
            {
                "name": value,
                "styleRefs": style_refs,
                "aliases": overrides.get("variantAliases", {}).get(value, []),
            }
        )

    return {
        "styleableName": styleable_name,
        "simpleName": simple_name,
        "className": class_name,
        "renderKind": overrides.get("renderKind", "xml_view"),
        "hostWidget": overrides.get("hostWidget"),
        "aliases": aliases,
        "xmlAttrs": styleable_entry["attrs"],
        "textStyleAttrs": _extract_text_style_attrs(styleable_entry["attrs"]),
        "textColorAttrs": _extract_text_color_attrs(styleable_entry["attrs"]),
        "variantAttr": variant_attr,
        "variants": variants,
        "sizeHints": overrides.get("sizeHints", {}),
    }


def _build_manual_widget_entry(
    manual_entry: dict,
    styleables: dict[str, dict],
    style_catalog: dict[str, dict],
    class_index: dict[str, str] | None = None,
    default_package: str = "wtcl.lib.widget",
) -> dict:
    styleable_name = manual_entry["styleableName"]
    copied_styleable = styleables.get(manual_entry.get("copyFromStyleable", ""), {"attrs": [], "enums": {}})
    styleable_entry = {
        "attrs": list(manual_entry.get("xmlAttrs", copied_styleable.get("attrs", []))),
        "enums": dict(manual_entry.get("xmlEnums", copied_styleable.get("enums", {}))),
    }
    overrides = {
        "simpleName": manual_entry.get("simpleName", styleable_name),
        "className": manual_entry["className"],
        "aliases": manual_entry.get("aliases", []),
        "variantAttr": manual_entry.get("variantAttr"),
        "variantAliases": manual_entry.get("variantAliases", {}),
        "variantStyleMap": manual_entry.get("variantStyleMap", {}),
        "sizeHints": manual_entry.get("sizeHints", {}),
        "renderKind": manual_entry.get("renderKind", "xml_view"),
        "hostWidget": manual_entry.get("hostWidget"),
    }
    return _build_widget_entry(
        styleable_name=styleable_name,
        styleable_entry=styleable_entry,
        overrides=overrides,
        style_catalog=style_catalog,
        class_index=class_index,
        default_package=default_package,
    )


def _build_registry(
    *,
    styleables: dict[str, dict],
    style_catalog: dict[str, dict],
    text_styles: list[dict],
    color_resources: list[dict],
    rules: dict,
    styleable_filter,
    class_index: dict[str, str],
    default_package: str,
    meta: dict | None = None,
) -> dict:
    widgets = []
    overrides = rules.get("widget_overrides", {})
    for styleable_name, styleable_entry in styleables.items():
        if not styleable_filter(styleable_name):
            continue
        widget_override = overrides.get(styleable_name, {})
        widgets.append(
            _build_widget_entry(
                styleable_name=styleable_name,
                styleable_entry=styleable_entry,
                overrides=widget_override,
                style_catalog=style_catalog,
                class_index=class_index,
                default_package=default_package,
            )
        )

    for manual_entry in rules.get("manual_widgets", []):
        widgets.append(
            _build_manual_widget_entry(
                manual_entry=manual_entry,
                styleables=styleables,
                style_catalog=style_catalog,
                class_index=class_index,
                default_package=default_package,
            )
        )

    registry_meta = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "widgetCount": len(widgets),
        "textStyleCount": len(text_styles),
        "colorResourceCount": len(color_resources),
    }
    registry_meta.update(meta or {})

    return {
        "meta": registry_meta,
        "widgets": sorted(widgets, key=lambda item: item["simpleName"]),
        "textStyles": sorted(text_styles, key=lambda item: item["name"]),
        "colorResources": sorted(
            (
                {
                    "name": item["name"],
                    "normalized": item["normalized"],
                }
                for item in color_resources
            ),
            key=lambda item: item["name"],
        ),
    }


def _write_registry(registry: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")


def build_widget_registry(widget_root: str, output_path: str, rules_path: str | None = None) -> dict:
    script_dir = Path(__file__).resolve().parent
    rules = _load_rules(script_dir, rules_path)
    widget_root_path = Path(widget_root)
    if _is_extracted_aar(widget_root_path):
        attrs_path = widget_root_path / "res" / "values" / "values.xml"
        class_index = _build_class_index_from_aar(widget_root_path)
    else:
        attrs_path = widget_root_path / "app" / "src" / "main" / "res" / "values" / "attrs.xml"
        class_index = {}
    styleables = _parse_attrs(attrs_path)
    style_catalog, text_styles, color_resources = _parse_style_catalog(widget_root_path)
    styleable_filter = _create_styleable_filter(
        {"mode": "prefix", "prefixes": ["WT", "Wt"], "excludeSuffixes": ["Style", "DefaultAdapter", "Adapter"]},
        class_index,
    )
    registry = {
        **_build_registry(
            styleables=styleables,
            style_catalog=style_catalog,
            text_styles=text_styles,
            color_resources=color_resources,
            rules=rules,
            styleable_filter=styleable_filter,
            class_index=class_index,
            default_package="wtcl.lib.widget",
        )
    }

    _write_registry(registry, Path(output_path))
    return registry


def _provider_dir(provider_config: dict) -> Path:
    provider_path = provider_config.get("_providerPath") or provider_config.get("providerPath")
    if provider_path:
        return Path(provider_path).resolve().parent
    library_id = provider_config.get("libraryId")
    return DEFAULT_REFERENCES_DIR / "libraries" / library_id


def _is_cache_valid(library_dir: Path, aar_path: Path, snapshot_file: str = "widget_registry.snapshot.json") -> bool:
    snapshot_path = library_dir / snapshot_file
    if not snapshot_path.exists():
        return False
    with snapshot_path.open("r", encoding="utf-8") as f:
        meta = json.load(f).get("meta", {})
    if meta.get("aarSourcePath") != str(aar_path):
        return False
    return float(meta.get("aarLastModified", 0)) >= aar_path.stat().st_mtime


def build_registry_for_provider(provider_config: dict, project_root: str | Path, refresh: bool = False) -> dict:
    library_dir = _provider_dir(provider_config)
    snapshot_file = provider_config.get("snapshotFile", "widget_registry.snapshot.json")
    snapshot_path = library_dir / snapshot_file
    dependency = provider_config.get("aarDependency", {})
    aar_path = _discover_aar_path(
        Path(project_root),
        dependency.get("group", ""),
        dependency.get("artifact", ""),
        dependency.get("version", ""),
    )
    if not aar_path:
        raise FileNotFoundError(f"AAR not found for {dependency}")

    if not refresh and _is_cache_valid(library_dir, aar_path, snapshot_file):
        with snapshot_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    rules_path = library_dir / provider_config.get("rulesFile", "widget_semantic_rules.json")
    with rules_path.open("r", encoding="utf-8") as f:
        rules = json.load(f)

    class_index = _build_class_index_from_aar(aar_path)
    styleables = _parse_attrs(aar_path / "res" / "values" / "values.xml")
    text_style_patterns = provider_config.get("textStylePatterns", [])
    text_style_prefixes = provider_config.get("textStylePrefixes", [])
    style_catalog, text_styles, color_resources = _parse_style_catalog(
        aar_path,
        text_style_patterns=text_style_patterns,
        text_style_prefixes=text_style_prefixes,
    )
    styleable_filter = _create_styleable_filter(provider_config.get("styleableFilter", {}), class_index)
    registry = _build_registry(
        styleables=styleables,
        style_catalog=style_catalog,
        text_styles=text_styles,
        color_resources=color_resources,
        rules=rules,
        styleable_filter=styleable_filter,
        class_index=class_index,
        default_package=provider_config.get("defaultPackage", ""),
        meta={
            "libraryId": provider_config.get("libraryId"),
            "aarSourcePath": str(aar_path),
            "aarLastModified": aar_path.stat().st_mtime,
            "textStylePatterns": text_style_patterns,
            "textStylePrefixes": text_style_prefixes,
            "preferredTextAttrs": provider_config.get("preferredTextAttrs", []),
            "preferredColorAttrs": provider_config.get("preferredColorAttrs", []),
        },
    )

    _write_registry(registry, snapshot_path)
    return registry


def _load_provider(library: str | None) -> dict:
    config_path = DEFAULT_REFERENCES_DIR / "library_config.json"
    with config_path.open("r", encoding="utf-8") as f:
        config = json.load(f)
    library_id = library or config.get("activeLibrary")
    entry = config.get("libraries", {}).get(library_id)
    if not entry:
        raise KeyError(f"Unknown library: {library_id}")
    provider_path = DEFAULT_REFERENCES_DIR / entry["providerPath"]
    with provider_path.open("r", encoding="utf-8") as f:
        provider = json.load(f)
    provider["_providerPath"] = str(provider_path)
    return provider


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output_path", nargs="?", help="Path to write widget_registry.json")
    parser.add_argument("--widget-root", default=os.environ.get("WT_WIDGET_ROOT", DEFAULT_WIDGET_ROOT))
    parser.add_argument("--rules-path")
    parser.add_argument("--library", help="Registered library id from references/library_config.json")
    parser.add_argument("--project-root", default=str(Path.cwd()))
    parser.add_argument(
        "--refresh-snapshot",
        action="store_true",
        help="Write the registry to the checked-in snapshot path under references/.",
    )
    args = parser.parse_args()

    if args.library:
        registry = build_registry_for_provider(
            _load_provider(args.library),
            args.project_root,
            refresh=args.refresh_snapshot,
        )
        if args.output_path:
            _write_registry(registry, Path(args.output_path))
        return

    output_path = args.output_path
    if args.refresh_snapshot:
        output_path = str(DEFAULT_SNAPSHOT_PATH)
    if not output_path:
        parser.error("output_path is required unless --refresh-snapshot is used")

    build_widget_registry(
        widget_root=args.widget_root,
        output_path=output_path,
        rules_path=args.rules_path,
    )


if __name__ == "__main__":
    main()
