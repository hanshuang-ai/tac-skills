#!/usr/bin/env python3
"""
dsl_query.py -- bounded MasterGo DSL query helper.

This script lets the agent query small, depth-limited slices from the cached
MasterGo DSL JSON on disk. The agent should execute this script instead of
reading mastergo_raw.json directly or calling chat/MCP getDsl for subtrees.

Examples:
    python scripts/query/dsl_query.py node work/mastergo_raw.json --node-id 22:34699 --depth 1
    python scripts/query/dsl_query.py children work/mastergo_raw.json --node-id 22:34699 --depth 1 --max-children 10
    python scripts/query/dsl_query.py find work/mastergo_raw.json --type TEXT --name-contains title --limit 20
    python scripts/query/dsl_query.py ancestors work/mastergo_raw.json --node-id 22:34742

The output is always bounded JSON. Full raw DSL, full child trees, image URLs,
and pathData are omitted unless explicitly requested with tight limits.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Add scripts dir and parent dir to path for sibling imports when executed directly.
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mastergo_utils import resolve_font, resolve_paint, resolve_effect  # noqa: E402


DEFAULT_MAX_CHILDREN = 20
DEFAULT_MAX_TEXT = 80
DEFAULT_MAX_NAME = 80
DEFAULT_PATH_DATA_LIMIT = 160
BOUNDS_KEYS = ("relativeX", "relativeY", "width", "height")


@dataclass
class NodeRecord:
    node: dict[str, Any]
    source: str
    parent_id: str | None
    depth: int
    parent_relative: dict[str, float]
    raw: dict[str, float]


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _dsl_block(data: dict[str, Any]) -> dict[str, Any]:
    return data.get("dsl", data)


def _num(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except Exception:
        return default


def _trim(value: Any, limit: int) -> Any:
    if not isinstance(value, str):
        return value
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)] + "…"


def _sanitize_for_output(value: Any, *, max_text: int, max_name: int) -> Any:
    if isinstance(value, str):
        return _trim(value, max_text)
    if isinstance(value, list):
        return [_sanitize_for_output(v, max_text=max_text, max_name=max_name) for v in value[:20]]
    if isinstance(value, dict):
        result = {}
        for key, item in list(value.items())[:30]:
            result[_trim(str(key), max_name)] = _sanitize_for_output(
                item, max_text=max_text, max_name=max_name
            )
        return result
    return value


def _load_sources(paths: list[str]) -> tuple[dict[str, NodeRecord], dict[str, Any], list[str]]:
    index: dict[str, NodeRecord] = {}
    styles: dict[str, Any] = {}
    warnings: list[str] = []

    def walk(node: dict[str, Any], source: str, parent_id: str | None, depth: int, abs_x: float, abs_y: float) -> None:
        layout = node.get("layoutStyle") or {}
        rel_x = _num(layout.get("relativeX", 0))
        rel_y = _num(layout.get("relativeY", 0))
        width = _num(layout.get("width", 0))
        height = _num(layout.get("height", 0))
        raw_x = abs_x + rel_x
        raw_y = abs_y + rel_y
        node_id = node.get("id")
        if node_id:
            record = NodeRecord(
                node=node,
                source=source,
                parent_id=parent_id,
                depth=depth,
                parent_relative={"x": rel_x, "y": rel_y, "width": width, "height": height},
                raw={"x": raw_x, "y": raw_y, "width": width, "height": height},
            )
            if node_id in index:
                warnings.append(f"duplicate node id '{node_id}' from {source}; keeping first occurrence")
            else:
                index[node_id] = record
        for child in node.get("children") or []:
            if isinstance(child, dict):
                walk(child, source, node_id, depth + 1, raw_x, raw_y)

    for raw_path in paths:
        path = Path(raw_path)
        data = _read_json(path)
        dsl = _dsl_block(data)
        styles.update(dsl.get("styles") or {})
        for root in dsl.get("nodes") or []:
            if isinstance(root, dict):
                walk(root, str(path), None, 0, 0.0, 0.0)

    return index, styles, warnings


def _paint_summary(ref: Any, styles: dict[str, Any], *, include_urls: bool) -> dict[str, Any] | None:
    if not isinstance(ref, str):
        return None
    paint = resolve_paint(ref, styles)
    if not paint:
        return {"ref": ref, "unresolved": True}
    value = paint.get("value")
    if paint.get("type") == "image" and not include_urls:
        value = "[URL_OMITTED]"
    return {
        "ref": ref,
        "type": paint.get("type"),
        "token": paint.get("token"),
        "value": value,
    }


def _font_summary(ref: Any, styles: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(ref, str):
        return None
    font = resolve_font(ref, styles)
    if not font:
        return {"ref": ref, "unresolved": True}
    return {"ref": ref, **font}


def _effect_summary(ref: Any, styles: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(ref, str):
        return None
    effect = resolve_effect(ref, styles)
    if not effect:
        return {"ref": ref, "unresolved": True}
    return {"ref": ref, "effects": effect[:5], "truncated": len(effect) > 5}


def _extract_text(node: dict[str, Any], styles: dict[str, Any], max_text: int) -> dict[str, Any] | None:
    text_segments = node.get("text")
    text_colors = node.get("textColor") or []
    if node.get("type") != "TEXT" and not text_segments:
        return None

    raw_text = ""
    font_refs: list[str] = []
    if isinstance(text_segments, list):
        for segment in text_segments:
            if not isinstance(segment, dict):
                continue
            raw_text += str(segment.get("text", ""))
            font_ref = segment.get("font")
            if isinstance(font_ref, str) and font_ref not in font_refs:
                font_refs.append(font_ref)
    elif isinstance(text_segments, str):
        raw_text = text_segments

    color_refs: list[str] = []
    if isinstance(text_colors, list):
        for color in text_colors:
            if isinstance(color, dict) and isinstance(color.get("color"), str):
                ref = color["color"]
                if ref not in color_refs:
                    color_refs.append(ref)

    return {
        "rawText": _trim(raw_text, max_text),
        "textLength": len(raw_text),
        "fontRefs": [_font_summary(ref, styles) for ref in font_refs[:4]],
        "colorRefs": [_paint_summary(ref, styles, include_urls=False) for ref in color_refs[:4]],
        "truncated": len(raw_text) > max_text or len(font_refs) > 4 or len(color_refs) > 4,
    }


def _extract_path(node: dict[str, Any], styles: dict[str, Any], *, include_path_data: bool, path_data_limit: int) -> dict[str, Any] | None:
    paths = node.get("path") or []
    if node.get("type") != "PATH" and not paths:
        return None
    summaries = []
    for item in paths[:5]:
        if not isinstance(item, dict):
            continue
        data = item.get("data", "")
        summary = {
            "hasData": bool(data),
            "dataLength": len(data) if isinstance(data, str) else 0,
            "fill": _paint_summary(item.get("fill"), styles, include_urls=False) or item.get("fill"),
        }
        if include_path_data and isinstance(data, str):
            summary["data"] = _trim(data, path_data_limit)
            summary["dataTruncated"] = len(data) > path_data_limit
        summaries.append(summary)
    return {"pathCount": len(paths), "paths": summaries, "truncated": len(paths) > 5}


def _node_summary(
    record: NodeRecord,
    index: dict[str, NodeRecord],
    styles: dict[str, Any],
    *,
    depth: int,
    max_children: int,
    max_text: int,
    max_name: int,
    include_urls: bool,
    include_path_data: bool,
    path_data_limit: int,
    fields: set[str],
) -> dict[str, Any]:
    node = record.node
    children = [child for child in (node.get("children") or []) if isinstance(child, dict)]

    result: dict[str, Any] = {
        "id": node.get("id"),
        "name": _trim(node.get("name", ""), max_name),
        "type": node.get("type"),
        "source": record.source,
        "parentId": record.parent_id,
        "treeDepth": record.depth,
        "childCount": len(children),
    }
    if node.get("componentId"):
        result["componentId"] = node.get("componentId")

    if "geometry" in fields:
        result["bounds"] = {
            "parent_relative": record.parent_relative,
            "raw": record.raw,
        }
        layout = node.get("layoutStyle") or {}
        extra_layout = {
            key: layout.get(key)
            for key in ("layoutMode", "layoutWrap", "fixPos", "rotation")
            if key in layout
        }
        if extra_layout:
            result["layoutStyleExtra"] = extra_layout

    if "styles" in fields:
        styles_out: dict[str, Any] = {}
        if node.get("fill"):
            styles_out["fill"] = _paint_summary(node.get("fill"), styles, include_urls=include_urls)
        if node.get("strokeColor"):
            styles_out["strokeColor"] = _paint_summary(node.get("strokeColor"), styles, include_urls=include_urls)
        if node.get("strokeWidth") is not None:
            styles_out["strokeWidth"] = node.get("strokeWidth")
        if node.get("borderRadius") is not None:
            styles_out["borderRadius"] = node.get("borderRadius")
        if node.get("effect"):
            styles_out["effect"] = _effect_summary(node.get("effect"), styles)
        if styles_out:
            result["styles"] = styles_out

    if "semantics" in fields:
        component_info = node.get("componentInfo") or {}
        if component_info:
            result["componentInfo"] = _sanitize_for_output(
                {
                    "description": component_info.get("description"),
                    "componentSetDescription": component_info.get("componentSetDescription"),
                    "properties": component_info.get("properties"),
                    "componentSetDocumentLink": component_info.get("componentSetDocumentLink"),
                },
                max_text=max_text,
                max_name=max_name,
            )

    if "text" in fields:
        text = _extract_text(node, styles, max_text)
        if text:
            result["text"] = text

    if "path" in fields:
        path = _extract_path(
            node,
            styles,
            include_path_data=include_path_data,
            path_data_limit=path_data_limit,
        )
        if path:
            result["path"] = path

    if "children" in fields:
        child_refs = [child.get("id") for child in children if child.get("id")]
        result["children"] = {
            "count": len(children),
            "ids": child_refs[:max_children],
            "truncated": len(children) > max_children,
        }
        if depth > 0:
            result["children"]["items"] = []
            for child in children[:max_children]:
                child_id = child.get("id")
                child_record = index.get(child_id) if child_id else None
                if child_record:
                    result["children"]["items"].append(
                        _node_summary(
                            child_record,
                            index,
                            styles,
                            depth=depth - 1,
                            max_children=max_children,
                            max_text=max_text,
                            max_name=max_name,
                            include_urls=include_urls,
                            include_path_data=include_path_data,
                            path_data_limit=path_data_limit,
                            fields=fields - {"children"} if depth - 1 <= 0 else fields,
                        )
                    )

    return result


def _compact_record(record: NodeRecord, *, max_name: int) -> dict[str, Any]:
    node = record.node
    return {
        "id": node.get("id"),
        "name": _trim(node.get("name", ""), max_name),
        "type": node.get("type"),
        "componentId": node.get("componentId"),
        "parentId": record.parent_id,
        "treeDepth": record.depth,
        "bounds": {
            "parent_relative": record.parent_relative,
            "raw": record.raw,
        },
        "childCount": len(node.get("children") or []),
    }


def _parse_fields(value: str) -> set[str]:
    if value == "all":
        return {"geometry", "styles", "semantics", "text", "path", "children"}
    fields = {item.strip() for item in value.split(",") if item.strip()}
    allowed = {"geometry", "styles", "semantics", "text", "path", "children"}
    unknown = fields - allowed
    if unknown:
        raise SystemExit(f"Unknown --fields entries: {', '.join(sorted(unknown))}")
    return fields or {"geometry", "styles", "text", "path", "children"}


def _base_payload(args: argparse.Namespace) -> tuple[dict[str, NodeRecord], dict[str, Any], list[str], set[str]]:
    index, styles, warnings = _load_sources(args.input_json)
    fields = _parse_fields(getattr(args, "fields", "geometry,styles,text,path,children"))
    return index, styles, warnings, fields


def cmd_node(args: argparse.Namespace) -> dict[str, Any]:
    index, styles, warnings, fields = _base_payload(args)
    record = index.get(args.node_id)
    if not record:
        return {"status": "NOT_FOUND", "nodeId": args.node_id, "warnings": warnings}
    return {
        "status": "OK",
        "query": {"command": "node", "nodeId": args.node_id, "depth": args.depth},
        "limits": _limits(args),
        "warnings": warnings,
        "node": _node_summary(
            record,
            index,
            styles,
            depth=args.depth,
            max_children=args.max_children,
            max_text=args.max_text,
            max_name=args.max_name,
            include_urls=args.include_urls,
            include_path_data=args.include_path_data,
            path_data_limit=args.path_data_limit,
            fields=fields,
        ),
    }


def cmd_children(args: argparse.Namespace) -> dict[str, Any]:
    index, styles, warnings, fields = _base_payload(args)
    record = index.get(args.node_id)
    if not record:
        return {"status": "NOT_FOUND", "nodeId": args.node_id, "warnings": warnings}
    children = [child for child in record.node.get("children") or [] if isinstance(child, dict)]
    items = []
    for child in children[: args.max_children]:
        child_id = child.get("id")
        child_record = index.get(child_id) if child_id else None
        if child_record:
            items.append(
                _node_summary(
                    child_record,
                    index,
                    styles,
                    depth=max(0, args.depth - 1),
                    max_children=args.max_children,
                    max_text=args.max_text,
                    max_name=args.max_name,
                    include_urls=args.include_urls,
                    include_path_data=args.include_path_data,
                    path_data_limit=args.path_data_limit,
                    fields=fields,
                )
            )
    return {
        "status": "OK",
        "query": {"command": "children", "nodeId": args.node_id, "depth": args.depth},
        "limits": _limits(args),
        "warnings": warnings,
        "parent": _compact_record(record, max_name=args.max_name),
        "children": {"count": len(children), "truncated": len(children) > args.max_children, "items": items},
    }


def cmd_ancestors(args: argparse.Namespace) -> dict[str, Any]:
    index, _styles, warnings, _fields = _base_payload(args)
    record = index.get(args.node_id)
    if not record:
        return {"status": "NOT_FOUND", "nodeId": args.node_id, "warnings": warnings}
    chain = []
    current = record
    while current:
        chain.append(_compact_record(current, max_name=args.max_name))
        if not current.parent_id:
            break
        current = index.get(current.parent_id)
    chain.reverse()
    return {
        "status": "OK",
        "query": {"command": "ancestors", "nodeId": args.node_id},
        "warnings": warnings,
        "ancestors": chain,
    }


def cmd_find(args: argparse.Namespace) -> dict[str, Any]:
    index, _styles, warnings, _fields = _base_payload(args)
    name_re = re.compile(args.name_regex, re.IGNORECASE) if args.name_regex else None
    matches = []
    for record in index.values():
        node = record.node
        if args.type and node.get("type") != args.type:
            continue
        if args.component_id and node.get("componentId") != args.component_id:
            continue
        if args.id_contains and args.id_contains not in str(node.get("id", "")):
            continue
        if args.name_contains and args.name_contains.lower() not in str(node.get("name", "")).lower():
            continue
        if name_re and not name_re.search(str(node.get("name", ""))):
            continue
        if args.has_text and not (node.get("type") == "TEXT" or node.get("text")):
            continue
        if args.has_fill and not node.get("fill"):
            continue
        matches.append(_compact_record(record, max_name=args.max_name))
        if len(matches) >= args.limit:
            break
    total_hint = len(matches)
    return {
        "status": "OK",
        "query": {
            "command": "find",
            "type": args.type,
            "componentId": args.component_id,
            "nameContains": args.name_contains,
            "idContains": args.id_contains,
            "limit": args.limit,
        },
        "warnings": warnings,
        "matches": matches,
        "returned": len(matches),
        "truncatedByLimit": total_hint >= args.limit,
    }


def _limits(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "depth": getattr(args, "depth", None),
        "maxChildren": getattr(args, "max_children", None),
        "maxText": getattr(args, "max_text", None),
        "maxName": getattr(args, "max_name", None),
        "includeUrls": getattr(args, "include_urls", False),
        "includePathData": getattr(args, "include_path_data", False),
        "pathDataLimit": getattr(args, "path_data_limit", None),
    }


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("input_json", nargs="+", help="Cached DSL JSON file(s), e.g. mastergo_raw.json and optional comp_*.json")
    parser.add_argument("--output", help="Optional file path for the bounded query JSON. Stdout prints only a small summary when set")
    parser.add_argument("--max-name", type=int, default=DEFAULT_MAX_NAME, help="Max name string length in output")
    parser.add_argument("--max-text", type=int, default=DEFAULT_MAX_TEXT, help="Max text string length in output")
    parser.add_argument("--fields", default="geometry,styles,text,path,children", help="Comma list: geometry,styles,semantics,text,path,children or all")


def _add_bounded(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--depth", type=int, default=1, help="Child recursion depth to include; keep small")
    parser.add_argument("--max-children", type=int, default=DEFAULT_MAX_CHILDREN, help="Max children returned per node")
    parser.add_argument("--include-urls", action="store_true", help="Include raw image URLs. Off by default to keep output small")
    parser.add_argument("--include-path-data", action="store_true", help="Include truncated pathData. Off by default")
    parser.add_argument("--path-data-limit", type=int, default=DEFAULT_PATH_DATA_LIMIT, help="Max pathData chars when included")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bounded query tool for cached MasterGo DSL JSON.")
    sub = parser.add_subparsers(dest="command", required=True)

    node = sub.add_parser("node", help="Return one node with bounded child depth")
    _add_common(node)
    _add_bounded(node)
    node.add_argument("--node-id", required=True)
    node.set_defaults(func=cmd_node)

    children = sub.add_parser("children", help="Return direct children of one node, optionally with shallow descendants")
    _add_common(children)
    _add_bounded(children)
    children.add_argument("--node-id", required=True)
    children.set_defaults(func=cmd_children)

    ancestors = sub.add_parser("ancestors", help="Return a compact ancestor chain for one node")
    _add_common(ancestors)
    ancestors.add_argument("--node-id", required=True)
    ancestors.set_defaults(func=cmd_ancestors)

    find = sub.add_parser("find", help="Search compact node index with filters and a strict limit")
    _add_common(find)
    find.add_argument("--type")
    find.add_argument("--component-id")
    find.add_argument("--name-contains")
    find.add_argument("--name-regex")
    find.add_argument("--id-contains")
    find.add_argument("--has-text", action="store_true")
    find.add_argument("--has-fill", action="store_true")
    find.add_argument("--limit", type=int, default=20)
    find.set_defaults(func=cmd_find)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if getattr(args, "depth", 0) is not None and getattr(args, "depth", 0) < 0:
        print("--depth must be >= 0", file=sys.stderr)
        return 2
    if getattr(args, "max_children", 1) is not None and getattr(args, "max_children", 1) < 1:
        print("--max-children must be >= 1", file=sys.stderr)
        return 2
    if getattr(args, "limit", 1) is not None and getattr(args, "limit", 1) < 1:
        print("--limit must be >= 1", file=sys.stderr)
        return 2

    payload = args.func(args)
    if getattr(args, "output", None):
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        summary = {
            "status": payload.get("status"),
            "output": str(output_path),
            "query": payload.get("query"),
            "returned": payload.get("returned"),
        }
        if "node" in payload:
            summary["nodeId"] = payload["node"].get("id")
            summary["childCount"] = payload["node"].get("childCount")
        if "children" in payload:
            summary["childCount"] = payload["children"].get("count")
            summary["childrenReturned"] = len(payload["children"].get("items", []))
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
