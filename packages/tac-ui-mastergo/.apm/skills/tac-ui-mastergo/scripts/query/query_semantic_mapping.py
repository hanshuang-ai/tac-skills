#!/usr/bin/env python3
"""
query_semantic_mapping.py -- Query semantic mapping details for a list of node IDs.

Supports querying node details from the unified semantic_mapping.json file.
Can accept node IDs as command-line arguments or via standard input (stdin).
Outputs result as JSON or formatted text summary.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_MAPPING_PATH = Path(__file__).resolve().parent.parent.parent / "sample" / "semantic_mapping.json"


def load_semantic_mapping(mapping_path: Path) -> dict:
    """Load semantic mapping JSON file."""
    if not mapping_path.exists():
        raise FileNotFoundError(f"Semantic mapping file not found at: {mapping_path}")

    with mapping_path.open("r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON file {mapping_path}: {e}")


def build_node_index(mapping_data: dict) -> dict[str, dict]:
    """Build a mapping from nodeId to the node dictionary for fast lookup."""
    index = {}
    nodes = mapping_data.get("nodes", [])
    for node in nodes:
        node_id = node.get("nodeId")
        if node_id:
            index[node_id] = node
    return index


def parse_stdin_ids() -> list[str]:
    """Parse node IDs from standard input, splitting by whitespace, commas, or newlines."""
    ids = []
    if not sys.stdin.isatty():
        raw_input = sys.stdin.read()
        # Split by comma or whitespace
        for token in raw_input.replace(",", " ").split():
            clean_token = token.strip().strip('"\'')
            if clean_token:
                ids.append(clean_token)
    return ids


def format_text_summary(node_id: str, node: dict | None) -> str:
    """Format a single node's details as a human-readable text summary."""
    if not node:
        return f"Node ID: {node_id}\n  [NOT FOUND in semantic mapping]\n"

    lines = []
    node_type = node.get("nodeType", "UNKNOWN")
    lines.append(f"Node ID: {node_id} ({node_type})")

    evidence = node.get("evidence", [])
    if evidence:
        lines.append(f"  Evidence: {', '.join(evidence)}")

    unresolved = node.get("unresolved", [])
    if unresolved:
        lines.append(f"  Unresolved Issues:")
        for issue in unresolved:
            lines.append(f"    - {issue}")

    resources = node.get("resources")
    if resources:
        lines.append(f"  Resources:")
        for k, v in resources.items():
            lines.append(f"    {k}: {v}")

    text_info = node.get("text")
    if text_info:
        lines.append(f"  Text Info:")
        raw_text = text_info.get("rawText", "")
        lines.append(f"    Raw Text: \"{raw_text}\"")
        style_token = text_info.get("styleToken")
        if style_token:
            lines.append(f"    Style Token: {style_token}")
        font = text_info.get("font")
        if font:
            lines.append(f"    Font: {json.dumps(font)}")
        color_token = text_info.get("colorToken")
        color_val = text_info.get("colorValue")
        if color_token or color_val:
            lines.append(f"    Color: {color_val} (Token: {color_token})")

    widget = node.get("widget")
    if widget:
        lines.append(f"  Widget Mapping:")
        for k, v in widget.items():
            lines.append(f"    {k}: {v}")

    widget_state = node.get("widgetState")
    if widget_state:
        lines.append(f"  Widget State: {json.dumps(widget_state)}")

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query matching attributes and resolved widget/text details in semantic_mapping.json by node IDs."
    )
    parser.add_argument(
        "ids",
        nargs="*",
        help="One or more Node IDs to query. E.g., '22:54400/20:05858'"
    )
    parser.add_argument(
        "-m",
        "--mapping",
        default=str(DEFAULT_MAPPING_PATH),
        help=f"Path to semantic_mapping.json. Defaults to: {DEFAULT_MAPPING_PATH}"
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read node IDs from standard input instead of/in addition to positional arguments."
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["json", "summary"],
        default="json",
        help="Output format: 'json' (default machine-readable) or 'summary' (human-readable text)."
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # Collect query IDs
    query_ids = list(args.ids)
    if args.stdin or (not query_ids and not sys.stdin.isatty()):
        query_ids.extend(parse_stdin_ids())

    if not query_ids:
        print("Error: No node IDs provided. Pass node IDs as arguments or pipe them via stdin.", file=sys.stderr)
        return 1

    # Load semantic mapping
    mapping_path = Path(args.mapping)
    try:
        mapping_data = load_semantic_mapping(mapping_path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Index nodes for fast lookup
    node_index = build_node_index(mapping_data)

    # Process queries
    results = {}
    missing = []

    for q_id in query_ids:
        if q_id in node_index:
            results[q_id] = node_index[q_id]
        else:
            missing.append(q_id)

    if args.format == "json":
        output = {
            "results": results,
            "missing": missing
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        # Output summary format
        print("=== SEMANTIC MAPPING QUERY RESULTS ===")
        print(f"Loaded mapping: {mapping_path.resolve()}")
        print(f"Query IDs: {', '.join(query_ids)}")
        print(f"Found: {len(results)}, Missing: {len(missing)}")
        print("-" * 50)

        for q_id in query_ids:
            node = results.get(q_id)
            print(format_text_summary(q_id, node))

    return 0


if __name__ == "__main__":
    sys.exit(main())
