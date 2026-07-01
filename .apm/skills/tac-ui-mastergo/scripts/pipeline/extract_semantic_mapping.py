#!/usr/bin/env python3
"""
extract_semantic_mapping.py -- Build a unified semantic mapping artifact.

This script trusts DSL semantic/style fields by default and only records
`unresolved` when the DSL or widget registry cannot support a direct mapping.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from mastergo_utils import resolve_font, resolve_paint


DEFAULT_TEXT_STYLE_PATTERNS = [r"^(WTTextStyle[A-Za-z0-9]+?)([RB])?$"]
DEFAULT_TEXT_STYLE_PREFIXES = ["WTTextStyle"]
DEFAULT_PREFERRED_TEXT_ATTRS = ["wtTextStyle", "wtDefaultTextStyle"]
DEFAULT_PREFERRED_COLOR_ATTRS = [
    "wtTextColor",
    "android:textColor",
    "wtDataTextColor",
    "wtSubTextColor",
    "wtItemTextColor",
    "wtDialogTitleTextColor",
    "wtDialogMessageTextColor",
    "wtDialogButtonTextColor",
]


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def _collect_lookup_keys(values: list[str]) -> list[str]:
    keys = []
    for value in values:
        if not value:
            continue
        normalized = _normalize(value)
        if normalized:
            keys.append(normalized)
        for token in re.findall(r"[A-Za-z0-9_]+", value):
            normalized_token = _normalize(token)
            if normalized_token:
                keys.append(normalized_token)
    return _dedupe_keep_order(keys)


def _load_mastergo_dsl(input_path: str) -> tuple[dict, list[dict], dict]:
    with open(input_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    dsl = raw.get("dsl", raw)
    styles = dsl.get("styles", {})
    nodes = dsl.get("nodes", [])
    return raw, nodes, styles


def _load_registry(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _extract_token_tail(token: str | None) -> str | None:
    if not token:
        return None
    parts = [part for part in re.split(r"[\\/]", token) if part]
    return parts[-1] if parts else token


def _create_text_style_matcher(patterns: list[str], prefixes: list[str]):
    compiled_patterns = [re.compile(pattern) for pattern in patterns if pattern]

    def extract_family(style_name: str | None) -> tuple[str | None, str | None]:
        if not style_name:
            return None, None
        for pattern in compiled_patterns:
            match = pattern.match(style_name)
            if match:
                family = match.group(1) if match.lastindex and match.lastindex >= 1 else style_name
                variant = match.group(2) if match.lastindex and match.lastindex >= 2 else None
                return family, variant
        return style_name, None

    def is_library_style(style_name: str | None) -> bool:
        return bool(style_name and any(style_name.startswith(prefix) for prefix in prefixes))

    return extract_family, is_library_style


def _load_library_semantic_config(registry: dict) -> dict:
    meta = registry.get("meta") or {}
    patterns = meta.get("textStylePatterns") or DEFAULT_TEXT_STYLE_PATTERNS
    prefixes = meta.get("textStylePrefixes") or DEFAULT_TEXT_STYLE_PREFIXES
    preferred_text_attrs = meta.get("preferredTextAttrs") or DEFAULT_PREFERRED_TEXT_ATTRS
    preferred_color_attrs = meta.get("preferredColorAttrs") or DEFAULT_PREFERRED_COLOR_ATTRS
    extract_family, is_library_style = _create_text_style_matcher(patterns, prefixes)
    return {
        "extractTextStyleFamily": extract_family,
        "isLibraryTextStyleName": is_library_style,
        "preferredTextAttrs": preferred_text_attrs,
        "preferredColorAttrs": preferred_color_attrs,
    }


def _infer_variant_from_weight(font_weight: int | float | None) -> str | None:
    if font_weight is None:
        return None
    return "B" if font_weight >= 600 else "R"


def _extract_text_name_signals(node_name: str | None, semantic_config: dict) -> dict:
    if not node_name:
        return {}
    result = {}
    style_match = re.search(r"style:\s*([A-Za-z0-9_.]+)", node_name, re.IGNORECASE)
    if style_match:
        style_name = style_match.group(1).strip()
        family, variant = semantic_config["extractTextStyleFamily"](style_name)
        result["styleName"] = style_name
        result["styleFamily"] = family
        if variant:
            result["styleVariant"] = variant

    color_match = re.search(r"#color:\s*([A-Za-z0-9_]+)", node_name, re.IGNORECASE)
    if color_match:
        result["colorToken"] = color_match.group(1).strip()
    return result


def _canonicalize_property_style_family(value: str | None, semantic_config: dict) -> str | None:
    if not value:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if semantic_config["isLibraryTextStyleName"](candidate):
        family, _ = semantic_config["extractTextStyleFamily"](candidate)
        return family

    prefix = candidate.split("_", 1)[0]
    prefix = re.sub(r"[^A-Za-z0-9 ]+", " ", prefix).strip()
    match = re.match(r"([A-Za-z]+)\s*([0-9]+)$", prefix)
    if not match:
        return None
    return candidate


def _extract_text_property_signals(node: dict, semantic_config: dict) -> dict:
    component_info = node.get("componentInfo") or {}
    properties = component_info.get("properties") or {}
    result = {}
    if not isinstance(properties, dict):
        return result

    for value in properties.values():
        if not isinstance(value, str):
            continue
        family = _canonicalize_property_style_family(value, semantic_config)
        if family and not result.get("styleFamily"):
            result["styleFamily"] = family

        lowered = value.lower()
        if "regular" in lowered and not result.get("styleVariant"):
            result["styleVariant"] = "R"
        elif "bold" in lowered and not result.get("styleVariant"):
            result["styleVariant"] = "B"
    return result


def _build_registry_lookups(registry: dict) -> dict:
    widget_lookup: dict[str, list[dict]] = {}
    variant_lookup: dict[str, list[tuple[dict, str]]] = {}
    text_lookup: dict[str, dict] = {}
    text_family_lookup: dict[str, list[dict]] = {}
    color_lookup: dict[str, dict] = {}

    for item in registry.get("textStyles", []):
        normalized = item.get("normalized") or _normalize(item.get("name", ""))
        if normalized:
            text_lookup[normalized] = item
        family_normalized = item.get("familyNormalized") or _normalize(item.get("family", ""))
        if family_normalized:
            text_family_lookup.setdefault(family_normalized, []).append(item)

    for entries in text_family_lookup.values():
        entries.sort(key=lambda item: item["name"])

    for item in registry.get("colorResources", []):
        normalized = item.get("normalized") or _normalize(item.get("name", ""))
        if normalized:
            color_lookup[normalized] = item

    for widget in registry.get("widgets", []):
        for alias in widget.get("aliases", []):
            normalized_alias = _normalize(alias)
            if normalized_alias:
                widget_lookup.setdefault(normalized_alias, []).append(widget)
        simple_name = _normalize(widget["simpleName"])
        styleable_name = _normalize(widget["styleableName"])
        if simple_name:
            widget_lookup.setdefault(simple_name, []).append(widget)
        if styleable_name:
            widget_lookup.setdefault(styleable_name, []).append(widget)

        for variant in widget.get("variants", []):
            variant_name = variant["name"]
            normalized_variant = _normalize(variant_name)
            if normalized_variant:
                variant_lookup.setdefault(normalized_variant, []).append((widget, variant_name))
            for alias in variant.get("aliases", []):
                normalized_alias = _normalize(alias)
                if normalized_alias:
                    variant_lookup.setdefault(normalized_alias, []).append((widget, variant_name))

    return {
        "widgets": widget_lookup,
        "variants": variant_lookup,
        "textStyles": text_lookup,
        "textStyleFamilies": text_family_lookup,
        "colorResources": color_lookup,
    }


def _collect_signal_values(node: dict, styles: dict) -> tuple[list[str], list[str]]:
    values = []
    evidence = []

    component_info = node.get("componentInfo") or {}
    if component_info.get("description"):
        values.append(str(component_info["description"]))
        evidence.append("componentInfo.description")
    if component_info.get("componentSetDescription"):
        values.append(str(component_info["componentSetDescription"]))
        evidence.append("componentInfo.componentSetDescription")
    if isinstance(component_info.get("properties"), dict):
        for key, value in component_info["properties"].items():
            values.append(f"{key}:{value}")
            values.append(str(value))
        evidence.append("componentInfo.properties")

    name = node.get("name")
    if name:
        values.append(str(name))
        evidence.append("node.name")

    fill_ref = node.get("fill")
    if isinstance(fill_ref, str):
        paint = resolve_paint(fill_ref, styles)
        token = _extract_token_tail((paint or {}).get("token"))
        if token:
            values.append(token)
            evidence.append("styles.token")

    return values, evidence


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _collect_descendant_signal_values(node: dict, styles: dict, max_depth: int = 1) -> tuple[list[str], list[str]]:
    values = []
    evidence = []

    def _walk_children(current: dict, depth: int):
        if depth > max_depth:
            return
        for child in current.get("children", []):
            if not isinstance(child, dict):
                continue
            child_values, child_evidence = _collect_signal_values(child, styles)
            values.extend(child_values)
            evidence.extend(f"child.{item}" for item in child_evidence)
            _walk_children(child, depth + 1)

    _walk_children(node, 1)
    return _dedupe_keep_order(values), _dedupe_keep_order(evidence)


def _has_widget_identity_signal(node: dict) -> bool:
    component_info = node.get("componentInfo") or {}
    return bool(
        node.get("type") == "INSTANCE"
        or node.get("componentId")
        or component_info.get("description")
        or component_info.get("componentSetDescription")
    )


def _build_component_signal_catalog(nodes: list[dict], styles: dict) -> dict[str, dict]:
    catalog: dict[str, dict] = {}

    def _walk(node: dict):
        component_id = node.get("componentId")
        if component_id:
            entry = catalog.setdefault(component_id, {"values": [], "evidence": []})
            values, evidence = _collect_signal_values(node, styles)
            entry["values"].extend(values)
            entry["evidence"].extend(evidence)

            descendant_values, descendant_evidence = _collect_descendant_signal_values(node, styles, max_depth=1)
            entry["values"].extend(descendant_values)
            entry["evidence"].extend(descendant_evidence)

        for child in node.get("children", []):
            if isinstance(child, dict):
                _walk(child)

    for root in nodes:
        if isinstance(root, dict):
            _walk(root)

    for entry in catalog.values():
        entry["values"] = _dedupe_keep_order(entry["values"])
        entry["evidence"] = _dedupe_keep_order(entry["evidence"])
    return catalog


def _match_single_widget(values: list[str], lookups: dict) -> tuple[dict | None, list[str]]:
    matches = []
    lookup_keys = _collect_lookup_keys(values)
    for normalized in lookup_keys:
        matches.extend(lookups["widgets"].get(normalized, []))

    unique = {}
    for widget in matches:
        unique[widget["simpleName"]] = widget
    return (next(iter(unique.values())), list(unique)) if len(unique) == 1 else (None, list(unique))


def _match_widget_from_variants(values: list[str], lookups: dict) -> tuple[dict | None, str | None, list[str]]:
    matches: list[tuple[dict, str]] = []
    lookup_keys = _collect_lookup_keys(values)
    for normalized in lookup_keys:
        matches.extend(lookups["variants"].get(normalized, []))

    if not matches:
        return None, None, []

    unique_widgets = {}
    unique_pairs = {}
    for widget, variant_name in matches:
        unique_widgets[widget["simpleName"]] = widget
        unique_pairs[(widget["simpleName"], variant_name)] = (widget, variant_name)

    if len(unique_widgets) == 1 and len(unique_pairs) == 1:
        widget, variant_name = next(iter(unique_pairs.values()))
        return widget, variant_name, [widget.get("variantAttr", "variant")]
    return None, None, []


def _collect_exact_variant_signals(values: list[str], lookups: dict) -> list[str]:
    exact_variant_values = []
    for value in values:
        lookup_keys = _collect_lookup_keys([value])
        if any(lookup_key in lookups["variants"] for lookup_key in lookup_keys):
            exact_variant_values.append(value)
    return _dedupe_keep_order(exact_variant_values)


def _has_authoritative_widget_evidence(evidence: list[str]) -> bool:
    return "componentInfo.description" in evidence


def _resolve_variant(node: dict, widget: dict, values: list[str], lookups: dict) -> tuple[str | None, list[str], list[str]]:
    matches = []
    evidence = []
    unresolved = []
    lookup_keys = _collect_lookup_keys(values)

    for normalized in lookup_keys:
        for candidate_widget, variant_name in lookups["variants"].get(normalized, []):
            if candidate_widget["simpleName"] == widget["simpleName"]:
                matches.append(variant_name)

    matches = sorted(set(matches))
    if len(matches) == 1:
        evidence.append(widget.get("variantAttr", "variant"))
        return matches[0], evidence, unresolved

    if len(matches) > 1:
        layout_style = node.get("layoutStyle", {})
        height = layout_style.get("height") or 0
        size_hints = widget.get("sizeHints", {})
        for hint_prefix, config in size_hints.items():
            small_variant = f"{hint_prefix}_small"
            big_variant = f"{hint_prefix}_big"
            if small_variant in matches and big_variant in matches and config.get("smallMaxHeight"):
                if height and height <= config["smallMaxHeight"]:
                    evidence.append("layoutStyle.height")
                    return small_variant, evidence, unresolved
                evidence.append("layoutStyle.height")
                return big_variant, evidence, unresolved
        unresolved.append(f"ambiguous variant: {', '.join(matches)}")

    return None, evidence, unresolved


def _resolve_widget(
    node: dict,
    styles: dict,
    lookups: dict,
    component_catalog: dict[str, dict],
    inherited_widget: dict | None = None,
) -> tuple[dict | None, dict | None, list[str], list[str]]:
    if not _has_widget_identity_signal(node):
        return None, None, [], []

    values, evidence = _collect_signal_values(node, styles)
    values = _dedupe_keep_order(values)
    evidence = _dedupe_keep_order(evidence)
    widget, widget_matches = _match_single_widget(values, lookups)
    unresolved = []
    variant = None
    variant_evidence = []
    variant_unresolved = []

    component_id = node.get("componentId")
    if not widget and component_id and component_id in component_catalog:
        catalog_entry = component_catalog[component_id]
        merged_values = _dedupe_keep_order(values + catalog_entry.get("values", []))
        merged_evidence = evidence + [f"componentId:{component_id}.{item}" for item in catalog_entry.get("evidence", [])]
        merged_evidence = _dedupe_keep_order(merged_evidence)
        widget, widget_matches = _match_single_widget(merged_values, lookups)
        if widget:
            values = merged_values
            evidence = merged_evidence

    if not widget and node.get("type") == "INSTANCE":
        descendant_values, descendant_evidence = _collect_descendant_signal_values(node, styles, max_depth=1)
        variant_hint_values = _collect_exact_variant_signals(descendant_values, lookups)
        if not variant_hint_values and component_id and component_id in component_catalog:
            variant_hint_values = _collect_exact_variant_signals(component_catalog[component_id].get("values", []), lookups)
        if variant_hint_values:
            merged_values = _dedupe_keep_order(values + descendant_values)
            merged_evidence = _dedupe_keep_order(evidence + descendant_evidence)
            widget, inferred_variant, inferred_variant_evidence = _match_widget_from_variants(variant_hint_values, lookups)
            if widget:
                values = merged_values
                evidence = merged_evidence
                variant = inferred_variant
                variant_evidence.extend(inferred_variant_evidence)

    if not widget:
        if widget_matches:
            unresolved.append(f"ambiguous widget: {', '.join(sorted(widget_matches))}")
        elif component_id and node.get("type") == "INSTANCE" and not inherited_widget:
            unresolved.append("missing instance widget mapping from component master")
        return None, None, evidence, unresolved

    if not _has_authoritative_widget_evidence(evidence):
        return None, None, evidence, []

    if not variant:
        variant, variant_evidence, variant_unresolved = _resolve_variant(node, widget, values, lookups)
    unresolved.extend(variant_unresolved)
    result = {
        "className": widget["className"],
        "styleableName": widget["styleableName"],
    }
    render_kind = widget.get("renderKind") or "xml_view"
    if render_kind == "xml_view":
        result["xmlTag"] = widget["className"]
    else:
        result["renderKind"] = render_kind
        unresolved.append(f"runtime-only widget: {widget['simpleName']}")
        if widget.get("hostWidget"):
            result["hostWidget"] = widget["hostWidget"]
    if variant:
        result["variant"] = variant
    return result, widget, sorted(set(evidence + variant_evidence)), unresolved


def _is_checkable_widget(widget: dict | None) -> bool:
    if not widget:
        return False
    simple_name = _normalize(widget.get("simpleName", ""))
    return any(keyword in simple_name for keyword in ("switch", "checkbox", "checkbutton", "radio", "toggle"))


def _assign_state_value(state: dict, key: str, value: bool, unresolved: list[str]) -> None:
    if key in state and state[key] != value:
        unresolved.append(f"conflicting state: {key}")
        return
    state[key] = value


def _resolve_widget_state(node: dict, widget: dict | None) -> tuple[dict | None, dict, list[str], list[str]]:
    if not widget:
        return None, {}, [], []

    component_info = node.get("componentInfo") or {}
    properties = component_info.get("properties") or {}
    if not isinstance(properties, dict):
        return None, {}, [], []

    state = {}
    attrs = {}
    evidence = []
    unresolved = []
    is_checkable = _is_checkable_widget(widget)

    for value in properties.values():
        if not isinstance(value, str):
            continue
        normalized = _normalize(value)
        if not normalized:
            continue

        if is_checkable:
            if normalized in {"on", "checked", "open", "opened", "true"}:
                _assign_state_value(state, "checked", True, unresolved)
                evidence.append("componentInfo.properties")
                continue
            if normalized in {"off", "unchecked", "close", "closed", "false"}:
                _assign_state_value(state, "checked", False, unresolved)
                evidence.append("componentInfo.properties")
                continue

        if normalized in {"selected", "active", "activated"}:
            _assign_state_value(state, "selected", True, unresolved)
            evidence.append("componentInfo.properties")
            continue
        if normalized in {"unselected", "inactive", "deactivated"}:
            _assign_state_value(state, "selected", False, unresolved)
            evidence.append("componentInfo.properties")
            continue
        if normalized in {"enabled", "enable"}:
            _assign_state_value(state, "enabled", True, unresolved)
            evidence.append("componentInfo.properties")
            continue
        if normalized in {"disabled", "disable"}:
            _assign_state_value(state, "enabled", False, unresolved)
            evidence.append("componentInfo.properties")
            continue
        if normalized == "loading":
            _assign_state_value(state, "loading", True, unresolved)
            evidence.append("componentInfo.properties")

    if "checked" in state and is_checkable:
        attrs["android:checked"] = "true" if state["checked"] else "false"
    if "selected" in state:
        attrs["android:selected"] = "true" if state["selected"] else "false"
    if "enabled" in state:
        attrs["android:enabled"] = "true" if state["enabled"] else "false"

    if not state and not attrs and not unresolved:
        return None, {}, [], []
    return state or None, attrs, sorted(set(evidence)), sorted(set(unresolved))


def _pick_text_style_entry(
    style_token: str | None,
    style_family: str | None,
    style_variant: str | None,
    font_weight: int | float | None,
    lookups: dict,
    semantic_config: dict,
) -> tuple[dict | None, list[str]]:
    deferred_unresolved = []
    if style_token:
        exact = lookups["textStyles"].get(_normalize(style_token))
        if exact:
            return exact, []
        token_family, token_variant = semantic_config["extractTextStyleFamily"](style_token)
        if semantic_config["isLibraryTextStyleName"](token_family):
            deferred_unresolved.append(f"missing text style resource for token: {style_token}")
            style_family = style_family or token_family
            style_variant = style_variant or token_variant

    if not style_family:
        return None, deferred_unresolved

    family_entries = lookups["textStyleFamilies"].get(_normalize(style_family), [])
    if not family_entries:
        return None, deferred_unresolved + [f"missing text style family: {style_family}"]

    desired_variant = style_variant or _infer_variant_from_weight(font_weight)
    if desired_variant:
        variant_matches = [entry for entry in family_entries if entry.get("variant") == desired_variant]
        if len(variant_matches) == 1:
            return variant_matches[0], []
        if len(variant_matches) > 1:
            return None, deferred_unresolved + [f"ambiguous text style variant: {style_family}{desired_variant}"]

    if len(family_entries) == 1:
        return family_entries[0], []

    variantless_entries = [entry for entry in family_entries if not entry.get("variant")]
    if len(variantless_entries) == 1:
        return variantless_entries[0], []

    return None, deferred_unresolved + [f"ambiguous text style family: {style_family}"]


def _resolve_color_resource(token_tail: str | None, lookups: dict) -> tuple[str | None, list[str]]:
    if not token_tail:
        return None, []
    color_entry = lookups["colorResources"].get(_normalize(token_tail))
    if color_entry:
        return f"@color/{color_entry['name']}", []
    return None, [f"missing color resource for token: {token_tail}"]


def _extract_text_color_attrs(attr_names: list[str]) -> list[str]:
    return sorted(attr_name for attr_name in attr_names if "textcolor" in _normalize(attr_name))


def _resolve_owner_attr_ownership(
    owner_widget: dict | None,
    candidate_attrs: list[str],
    preferred_attrs: list[str],
) -> dict:
    if not owner_widget:
        return {"kind": "direct_text"}

    ownership = {
        "kind": "widget_default",
        "ownerWidget": owner_widget["simpleName"],
        "styleableName": owner_widget["styleableName"],
    }
    if candidate_attrs:
        ownership["candidateAttrs"] = candidate_attrs

    preferred_attr = None
    for attr_name in preferred_attrs:
        if attr_name in candidate_attrs:
            preferred_attr = attr_name
            break
    if not preferred_attr and len(candidate_attrs) == 1:
        preferred_attr = candidate_attrs[0]

    if preferred_attr:
        ownership["kind"] = "widget_attr"
        ownership["preferredAttr"] = preferred_attr
    return ownership


def _resolve_text_ownership(owner_widget: dict | None, preferred_attrs: list[str]) -> dict:
    candidate_attrs = owner_widget.get("textStyleAttrs", []) if owner_widget else []
    return _resolve_owner_attr_ownership(
        owner_widget,
        candidate_attrs,
        preferred_attrs,
    )


def _resolve_text_color_ownership(owner_widget: dict | None, preferred_attrs: list[str]) -> dict:
    candidate_attrs = []
    if owner_widget:
        candidate_attrs = owner_widget.get("textColorAttrs") or _extract_text_color_attrs(owner_widget.get("xmlAttrs", []))
    return _resolve_owner_attr_ownership(
        owner_widget,
        candidate_attrs,
        preferred_attrs,
    )


def _resolve_text_mapping(
    node: dict,
    styles: dict,
    lookups: dict,
    owner_widget: dict | None,
    semantic_config: dict,
) -> tuple[dict | None, list[str], list[str]]:
    if node.get("type") != "TEXT" and not node.get("text"):
        return None, [], []

    text_segments = node.get("text") or []
    text_colors = node.get("textColor") or []
    evidence = []
    unresolved = []
    conflicts = []
    result = {"rawText": "".join(segment.get("text", "") for segment in text_segments if isinstance(segment, dict))}

    name_signals = _extract_text_name_signals(node.get("name"), semantic_config)
    property_signals = _extract_text_property_signals(node, semantic_config)
    if name_signals:
        evidence.append("TEXT.name")
    if property_signals:
        evidence.append("componentInfo.properties")

    font_ref = None
    font_info = None
    style_token = None
    structured_style_family = None
    structured_style_variant = None
    font_weight = None
    if text_segments and isinstance(text_segments[0], dict):
        font_ref = text_segments[0].get("font")
    if font_ref:
        evidence.append("TEXT.text[].font")
        font_info = resolve_font(font_ref, styles)
        if font_info:
            font_weight = font_info.get("fontWeight")
            result["fontRef"] = font_ref
            result["font"] = {
                "fontFamily": font_info.get("fontFamily"),
                "fontSize": font_info.get("fontSize"),
                "fontWeight": font_weight,
                "lineHeight": font_info.get("lineHeight"),
                "letterSpacing": font_info.get("letterSpacing"),
            }
            style_token = _extract_token_tail(font_info.get("token"))
            if style_token:
                result["styleToken"] = style_token
                token_family, token_variant = semantic_config["extractTextStyleFamily"](style_token)
                if semantic_config["isLibraryTextStyleName"](token_family):
                    structured_style_family, structured_style_variant = token_family, token_variant
        else:
            unresolved.append(f"unresolved font ref: {font_ref}")

    style_family = structured_style_family or property_signals.get("styleFamily") or name_signals.get("styleFamily")
    style_variant = structured_style_variant or property_signals.get("styleVariant") or name_signals.get("styleVariant")
    style_entry, style_unresolved = _pick_text_style_entry(
        style_token,
        style_family,
        style_variant,
        font_weight,
        lookups,
        semantic_config,
    )
    unresolved.extend(style_unresolved)
    if style_entry:
        result["resolvedStyleName"] = style_entry["name"]
        result["styleRef"] = style_entry["styleRef"]
        result["styleFamily"] = style_entry.get("family")
        if style_entry.get("variant"):
            result["styleVariant"] = style_entry["variant"]
        result["styleSources"] = sorted(
            {
                source
                for source, value in (
                    ("TEXT.text[].font", font_ref),
                    ("componentInfo.properties", property_signals.get("styleFamily")),
                    ("TEXT.name", name_signals.get("styleFamily")),
                )
                if value
            }
        )
    elif style_family:
        result["styleFamily"] = style_family
        if style_variant:
            result["styleVariant"] = style_variant

    if name_signals.get("styleFamily") and result.get("styleFamily"):
        if _normalize(name_signals["styleFamily"]) != _normalize(result["styleFamily"]):
            conflicts.append(
                f"TEXT.name style={name_signals['styleFamily']} but resolved style family={result['styleFamily']}"
            )

    if property_signals.get("styleFamily") and result.get("styleFamily"):
        if _normalize(property_signals["styleFamily"]) != _normalize(result["styleFamily"]):
            conflicts.append(
                f"componentInfo.properties style={property_signals['styleFamily']} but resolved style family={result['styleFamily']}"
            )

    color_info = None
    structured_color_token = None
    color_ref_source = None
    if text_colors and isinstance(text_colors[0], dict):
        color_ref_source = text_colors[0].get("color")
    if color_ref_source:
        evidence.append("TEXT.textColor[]")
        paint_info = resolve_paint(color_ref_source, styles)
        if paint_info:
            result["colorRefSource"] = color_ref_source
            result["colorValue"] = paint_info.get("value")
            color_info = {
                "sources": ["TEXT.textColor[]"],
                "refSource": color_ref_source,
                "value": paint_info.get("value"),
            }
            structured_color_token = _extract_token_tail(paint_info.get("token"))
            if structured_color_token:
                result["colorToken"] = structured_color_token
                color_info["token"] = structured_color_token
                color_ref, color_unresolved = _resolve_color_resource(structured_color_token, lookups)
                unresolved.extend(color_unresolved)
                if color_ref:
                    result["colorRef"] = color_ref
                    result["colorSources"] = ["TEXT.textColor[]"]
                    color_info["ref"] = color_ref
        else:
            unresolved.append(f"unresolved color ref: {color_ref_source}")

    name_color_token = name_signals.get("colorToken")
    if name_color_token:
        if structured_color_token and _normalize(structured_color_token) != _normalize(name_color_token):
            conflicts.append(
                f"TEXT.name color={name_color_token} but TEXT.textColor[] resolves to {structured_color_token}"
            )
        elif not result.get("colorRef"):
            result["colorToken"] = name_color_token
            color_info = color_info or {"sources": ["TEXT.name"]}
            color_info["token"] = name_color_token
            color_ref, color_unresolved = _resolve_color_resource(name_color_token, lookups)
            unresolved.extend(color_unresolved)
            if color_ref:
                result["colorRef"] = color_ref
                result["colorSources"] = ["TEXT.name"]
                color_info["ref"] = color_ref

    if color_info:
        color_info["ownership"] = _resolve_text_color_ownership(
            owner_widget,
            semantic_config["preferredColorAttrs"],
        )
        result["color"] = color_info

    if conflicts:
        result["conflicts"] = sorted(set(conflicts))

    if result.get("styleRef"):
        result["ownership"] = _resolve_text_ownership(owner_widget, semantic_config["preferredTextAttrs"])
    elif owner_widget:
        result["ownership"] = _resolve_text_ownership(owner_widget, semantic_config["preferredTextAttrs"])

    if not result.get("styleRef") and not result.get("colorRef") and "font" not in result and not result.get("conflicts"):
        return None, sorted(set(evidence)), sorted(set(unresolved))
    return result, sorted(set(evidence)), sorted(set(unresolved))


def _resolve_fill_resource(node: dict, styles: dict, lookups: dict) -> tuple[dict | None, list[str], list[str]]:
    fill_ref = node.get("fill")
    if not isinstance(fill_ref, str):
        return None, [], []
    paint_info = resolve_paint(fill_ref, styles)
    if not paint_info:
        return None, [], [f"unresolved fill ref: {fill_ref}"]

    token_tail = _extract_token_tail(paint_info.get("token"))
    if not token_tail:
        return None, [], []

    color_ref, unresolved = _resolve_color_resource(token_tail, lookups)
    if color_ref:
        return {"fillColorRef": color_ref}, ["styles.token"], []

    return {"fillColorValue": paint_info.get("value"), "fillColorToken": token_tail}, ["styles.token"], unresolved


def _walk_nodes(
    nodes: list[dict],
    styles: dict,
    lookups: dict,
    component_catalog: dict[str, dict],
    semantic_config: dict,
) -> list[dict]:
    results = []

    def _walk(node: dict, inherited_widget: dict | None):
        widget_info, widget_entry, widget_evidence, widget_unresolved = _resolve_widget(
            node,
            styles,
            lookups,
            component_catalog,
            inherited_widget,
        )
        active_widget = widget_entry or inherited_widget
        state_info, state_attrs, state_evidence, state_unresolved = _resolve_widget_state(node, widget_entry)
        text_info, text_evidence, text_unresolved = _resolve_text_mapping(
            node,
            styles,
            lookups,
            active_widget,
            semantic_config,
        )
        fill_info, fill_evidence, fill_unresolved = _resolve_fill_resource(node, styles, lookups)

        attrs = {}
        if widget_info and widget_entry and widget_entry.get("variantAttr") and widget_info.get("variant"):
            attrs = {f"app:{widget_entry['variantAttr']}": widget_info["variant"]}
        attrs.update(state_attrs)

        unresolved = sorted(set(widget_unresolved + state_unresolved + text_unresolved + fill_unresolved))
        evidence = sorted(set(widget_evidence + state_evidence + text_evidence + fill_evidence))
        has_mapping = bool(widget_info or state_info or text_info or fill_info)
        if has_mapping:
            entry = {
                "nodeId": node.get("id"),
                "nodeType": node.get("type"),
                "evidence": evidence,
                "unresolved": unresolved,
            }
            if widget_info:
                entry["resolvedWidget"] = widget_info
            if attrs:
                entry["attrs"] = attrs
            if state_info:
                entry["state"] = state_info
            if text_info:
                entry["text"] = text_info
            if fill_info:
                entry["resources"] = fill_info
            results.append(entry)

        for child in node.get("children", []):
            if isinstance(child, dict):
                _walk(child, active_widget)

    for root in nodes:
        if isinstance(root, dict):
            _walk(root, None)

    return results


def extract_semantic_mapping(input_path: str, registry_path: str, output_path: str) -> dict:
    _, nodes, styles = _load_mastergo_dsl(input_path)
    registry = _load_registry(registry_path)
    semantic_config = _load_library_semantic_config(registry)
    lookups = _build_registry_lookups(registry)
    component_catalog = _build_component_signal_catalog(nodes, styles)
    mappings = _walk_nodes(nodes, styles, lookups, component_catalog, semantic_config)

    result = {
        "meta": {
            "source": os.path.abspath(input_path),
            "widgetRegistry": os.path.abspath(registry_path),
            "nodeCount": len(mappings),
        },
        "nodes": mappings,
    }

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path")
    parser.add_argument("registry_path")
    parser.add_argument("output_path")
    args = parser.parse_args()
    extract_semantic_mapping(args.input_path, args.registry_path, args.output_path)


if __name__ == "__main__":
    main()
