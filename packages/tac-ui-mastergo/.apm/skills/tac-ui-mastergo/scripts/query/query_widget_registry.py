#!/usr/bin/env python3
"""
Query the checked-in widget registry snapshot with progressive disclosure.

Default usage is summary-first so AI callers can inspect a small index result,
then re-run with --level detail or --level full for the selected entry.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent.parent.parent / "references" / "widget_registry.snapshot.json"


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def _load_registry(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _score_match(query: str, candidates: list[str]) -> int:
    normalized_query = _normalize(query)
    best = 0
    for candidate in candidates:
        normalized_candidate = _normalize(candidate)
        if not normalized_candidate:
            continue
        if normalized_candidate == normalized_query:
            best = max(best, 100)
        elif normalized_candidate.startswith(normalized_query) or normalized_query.startswith(normalized_candidate):
            best = max(best, 70)
        elif normalized_query in normalized_candidate:
            best = max(best, 40)
    return best


def _match_widgets(registry: dict, query: str) -> list[dict]:
    matches = []
    for entry in registry.get("widgets", []):
        candidates = [
            entry.get("simpleName", ""),
            entry.get("styleableName", ""),
            *entry.get("aliases", []),
            *(variant.get("name", "") for variant in entry.get("variants", [])),
        ]
        score = _score_match(query, candidates)
        if score:
            matches.append((score, entry))
    matches.sort(key=lambda item: (-item[0], item[1].get("simpleName", "")))
    return [entry for _, entry in matches]


def _match_text_styles(registry: dict, query: str) -> list[dict]:
    matches = []
    for entry in registry.get("textStyles", []):
        candidates = [
            entry.get("name", ""),
            entry.get("family", ""),
        ]
        score = _score_match(query, candidates)
        if score:
            matches.append((score, entry))
    matches.sort(key=lambda item: (-item[0], item[1].get("name", "")))
    return [entry for _, entry in matches]


def _match_colors(registry: dict, query: str) -> list[dict]:
    matches = []
    for entry in registry.get("colorResources", []):
        score = _score_match(query, [entry.get("name", "")])
        if score:
            matches.append((score, entry))
    matches.sort(key=lambda item: (-item[0], item[1].get("name", "")))
    return [entry for _, entry in matches]


def _summarize_widget(entry: dict) -> dict:
    return {
        "simpleName": entry.get("simpleName"),
        "className": entry.get("className"),
        "renderKind": entry.get("renderKind"),
        "hostWidget": entry.get("hostWidget"),
        "variantCount": len(entry.get("variants", [])),
        "attrCount": len(entry.get("xmlAttrs", [])),
        "textStyleAttrCount": len(entry.get("textStyleAttrs", [])),
        "aliases": entry.get("aliases", []),
    }


def _detail_widget(entry: dict) -> dict:
    return {
        "simpleName": entry.get("simpleName"),
        "styleableName": entry.get("styleableName"),
        "className": entry.get("className"),
        "renderKind": entry.get("renderKind"),
        "hostWidget": entry.get("hostWidget"),
        "aliases": entry.get("aliases", []),
        "xmlAttrs": entry.get("xmlAttrs", []),
        "textStyleAttrs": entry.get("textStyleAttrs", []),
        "variantAttr": entry.get("variantAttr"),
        "variants": [
            {
                "name": variant.get("name"),
                "styleRefs": variant.get("styleRefs", []),
                "aliases": variant.get("aliases", []),
            }
            for variant in entry.get("variants", [])
        ],
        "sizeHints": entry.get("sizeHints", {}),
    }


def _summarize_text_style(entry: dict) -> dict:
    return {
        "name": entry.get("name"),
        "styleRef": entry.get("styleRef"),
        "family": entry.get("family"),
        "variant": entry.get("variant"),
        "weight": entry.get("weight"),
    }


def _detail_text_style(entry: dict) -> dict:
    return {
        "name": entry.get("name"),
        "styleRef": entry.get("styleRef"),
        "family": entry.get("family"),
        "familyNormalized": entry.get("familyNormalized"),
        "variant": entry.get("variant"),
        "weight": entry.get("weight"),
        "metrics": entry.get("metrics", {}),
    }


def _summarize_color(entry: dict) -> dict:
    return {
        "name": entry.get("name"),
        "normalized": entry.get("normalized"),
    }


def _format_matches(kind: str, entries: list[dict], level: str, limit: int) -> list[dict]:
    formatted = []
    for entry in entries[:limit]:
        if kind == "widget":
            payload = (
                entry
                if level == "full"
                else _detail_widget(entry)
                if level == "detail"
                else _summarize_widget(entry)
            )
            label = entry.get("simpleName")
        elif kind == "text-style":
            payload = (
                entry
                if level == "full"
                else _detail_text_style(entry)
                if level == "detail"
                else _summarize_text_style(entry)
            )
            label = entry.get("name")
        else:
            payload = entry if level == "full" else _summarize_color(entry)
            label = entry.get("name")
        formatted.append(
            {
                "kind": kind,
                "label": label,
                "level": level,
                "availableLevels": ["summary", "detail", "full"],
                "data": payload,
            }
        )
    return formatted


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query the widget registry snapshot with progressive disclosure.")
    parser.add_argument("query", help="Widget / text-style / color query string")
    parser.add_argument(
        "--kind",
        choices=["auto", "widget", "text-style", "color"],
        default="auto",
        help="Restrict the search domain. Default searches all three.",
    )
    parser.add_argument(
        "--level",
        choices=["summary", "detail", "full"],
        default="summary",
        help="How much data to return for each match.",
    )
    parser.add_argument("--limit", type=int, default=5, help="Maximum matches per kind.")
    parser.add_argument(
        "--registry",
        default=str(DEFAULT_REGISTRY_PATH),
        help="Registry snapshot path. Defaults to the checked-in snapshot.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    registry_path = Path(args.registry)
    registry = _load_registry(registry_path)

    kinds = [args.kind] if args.kind != "auto" else ["widget", "text-style", "color"]
    matches = []

    for kind in kinds:
        if kind == "widget":
            entries = _match_widgets(registry, args.query)
        elif kind == "text-style":
            entries = _match_text_styles(registry, args.query)
        else:
            entries = _match_colors(registry, args.query)
        matches.extend(_format_matches(kind, entries, args.level, args.limit))

    result = {
        "query": args.query,
        "level": args.level,
        "registry": {
            "path": str(registry_path.resolve()),
            "generatedAt": registry.get("meta", {}).get("generatedAt"),
            "widgetCount": registry.get("meta", {}).get("widgetCount"),
            "textStyleCount": registry.get("meta", {}).get("textStyleCount"),
            "colorResourceCount": registry.get("meta", {}).get("colorResourceCount"),
        },
        "matches": matches,
        "nextStep": "Use --level detail or --level full for the selected label if more data is needed.",
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
