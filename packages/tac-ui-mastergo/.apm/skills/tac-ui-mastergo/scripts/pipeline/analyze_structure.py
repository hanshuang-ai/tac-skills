"""
Structural Pattern Analyzer (v2.0)
Detects repeating siblings, positional anchors, size clusters, and scroll candidates
from a normalized node_tree.json. Outputs structural_hints.json for LLM component analysis.

This script performs DETERMINISTIC pattern detection only.
It does NOT make semantic decisions (toolbar vs banner, list vs grid).
That is the LLM's job, guided by prompts/component_analysis.md.

Usage:
    python analyze_structure.py <node_tree.json> <output_structural_hints.json>
"""

import hashlib
import json
import logging
import os
import sys
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)

# Tolerances for pattern detection
POSITION_TOLERANCE_DP = 8       # dp tolerance for anchor detection
WIDTH_RATIO_THRESHOLD = 0.90    # >90% of parent width = "spans full width"
SIZE_CLUSTER_TOLERANCE = 4      # dp tolerance for size clustering
MIN_REPEATING_COUNT = 3         # Minimum siblings to count as "repeating"
MIN_LIST_METRIC_COUNT = 2       # Minimum siblings to compute list item pitch/gap
SCROLL_RATIO_THRESHOLD = 1.5    # Content > 1.5x viewport = scrollable
SPACING_SIGNIFICANCE_DP = 4     # Ignore computed spacing below this threshold
MAX_SPACING_CHILDREN = 30       # Skip spacing analysis for nodes with too many children


def _build_child_index(nodes: list[dict]) -> dict[str, list[dict]]:
    """Build a parent_id -> [child_nodes] index from flat node list.

    Each node has 'childIds' listing its children's IDs.
    """
    id_map = {n["id"]: n for n in nodes if "id" in n}
    parent_index = defaultdict(list)

    for node in nodes:
        for child_id in node.get("childIds", []):
            if child_id in id_map:
                parent_index[node["id"]].append(id_map[child_id])

    return parent_index, id_map


def _node_tree_from_mastergo(raw: dict) -> dict:
    """Normalize raw MasterGo DSL tree into the flat node tree used here."""
    dsl = raw.get("dsl", raw)
    roots = dsl.get("nodes", [])
    flat_nodes = []

    def walk(node: dict, parent_id: str | None, parent_abs_x: float, parent_abs_y: float) -> None:
        node_id = node.get("id", "")
        layout = node.get("layoutStyle", {}) or {}
        rel_x = float(layout.get("relativeX", 0) or 0)
        rel_y = float(layout.get("relativeY", 0) or 0)
        width = float(layout.get("width", 0) or 0)
        height = float(layout.get("height", 0) or 0)
        abs_x = parent_abs_x + rel_x
        abs_y = parent_abs_y + rel_y
        children = node.get("children", []) or []

        normalized = {
            "id": node_id,
            "name": node.get("name", ""),
            "type": node.get("type", ""),
            "dimensions": {"width": width, "height": height},
            "absolutePosition": {"x": abs_x, "y": abs_y},
            "relativePosition": {"x": rel_x, "y": rel_y},
            "childIds": [child.get("id", "") for child in children if child.get("id")],
        }
        if parent_id:
            normalized["parentId"] = parent_id
        for key in ("componentId", "strokeWidth", "strokeColor", "strokeAlign", "fill"):
            if key in node:
                normalized[key] = node[key]
        flat_nodes.append(normalized)

        for child in children:
            walk(child, node_id, abs_x, abs_y)

    for root in roots:
        walk(root, None, 0, 0)

    return {"nodes": flat_nodes}


def _node_tree_from_skeleton(skeleton_data: dict) -> dict:
    """Best-effort skeleton adapter. Prefer raw DSL when positions are needed."""
    root = skeleton_data.get("skeleton", skeleton_data)
    flat_nodes = []

    def walk(node: dict, parent_id: str | None, parent_abs_x: float, parent_abs_y: float) -> None:
        node_id = node.get("id", "")
        rel_x = float(node.get("x", 0) or 0)
        rel_y = float(node.get("y", 0) or 0)
        width = float(node.get("w", 0) or 0)
        height = float(node.get("h", 0) or 0)
        abs_x = parent_abs_x + rel_x
        abs_y = parent_abs_y + rel_y
        children = node.get("ch", []) or []
        normalized = {
            "id": node_id,
            "name": node.get("n", ""),
            "type": node.get("t", ""),
            "dimensions": {"width": width, "height": height},
            "absolutePosition": {"x": abs_x, "y": abs_y},
            "relativePosition": {"x": rel_x, "y": rel_y},
            "childIds": [child.get("id", "") for child in children if child.get("id")],
        }
        if parent_id:
            normalized["parentId"] = parent_id
        flat_nodes.append(normalized)
        for child in children:
            walk(child, node_id, abs_x, abs_y)

    if root:
        walk(root, None, 0, 0)
    return {"nodes": flat_nodes}


def _normalize_input_tree(node_tree: dict) -> dict:
    """Accept normalized trees, raw MasterGo DSL, or skeleton artifacts."""
    nodes = node_tree.get("nodes", [])
    if nodes and any("dimensions" in node and "absolutePosition" in node for node in nodes):
        return node_tree
    if node_tree.get("dsl") or (nodes and any("layoutStyle" in node for node in nodes)):
        return _node_tree_from_mastergo(node_tree)
    if node_tree.get("skeleton") or node_tree.get("ch"):
        return _node_tree_from_skeleton(node_tree)
    return node_tree


def _structure_hash(node: dict, id_map: dict) -> str:
    """Generate a hash representing a node's structural pattern.

    Captures child types and relative size proportions (not absolute values)
    to identify nodes that share the same visual template.
    """
    child_ids = node.get("childIds", [])
    if not child_ids:
        # Leaf node: hash by type only
        return hashlib.md5(node.get("type", "").encode()).hexdigest()[:8]

    # For non-leaf: hash by ordered child types + relative dimensions
    parts = []
    for cid in child_ids:
        child = id_map.get(cid, {})
        c_type = child.get("type", "?")
        c_dim = child.get("dimensions", {})
        w = round(c_dim.get("width", 0) / 10) * 10   # Round to nearest 10dp
        h = round(c_dim.get("height", 0) / 10) * 10
        parts.append(f"{c_type}:{w}x{h}")

    signature = "|".join(parts)
    return hashlib.md5(signature.encode()).hexdigest()[:8]


# ---------------------------------------------------------------------------
# Pattern Detectors
# ---------------------------------------------------------------------------

def detect_repeating_siblings(nodes: list[dict], parent_index: dict,
                               id_map: dict) -> list[dict]:
    """Detect groups of sibling nodes that share the same structural pattern.

    A repeating group is 3+ children of the same parent with matching structure hashes.
    """
    results = []

    for parent_id, children in parent_index.items():
        if len(children) < MIN_REPEATING_COUNT:
            continue

        # Group children by structure hash
        hash_groups = defaultdict(list)
        for child in children:
            h = _structure_hash(child, id_map)
            hash_groups[h].append(child)

        for hash_val, group in hash_groups.items():
            if len(group) < MIN_REPEATING_COUNT:
                continue

            parent = id_map.get(parent_id, {})
            sample = group[0]
            sample_dim = sample.get("dimensions", {})
            sample_child_types = [
                id_map.get(cid, {}).get("type", "?")
                for cid in sample.get("childIds", [])
            ]

            # Calculate confidence based on hash match ratio
            confidence = len(group) / len(children)

            results.append({
                "parent_node_id": parent_id,
                "parent_name": parent.get("name", ""),
                "children_count": len(group),
                "total_siblings": len(children),
                "child_structure_hash": hash_val,
                "sample_child": {
                    "node_id": sample.get("id", ""),
                    "name": sample.get("name", ""),
                    "child_types": sample_child_types,
                    "dimensions": {
                        "width": sample_dim.get("width", 0),
                        "height": sample_dim.get("height", 0),
                    },
                },
                "confidence": round(confidence, 2),
            })

    logger.info("Detected %d repeating sibling groups", len(results))
    return results


def detect_positional_anchors(nodes: list[dict], parent_index: dict,
                               id_map: dict) -> list[dict]:
    """Detect elements anchored to top or bottom of their parent.

    A positional anchor is a child that:
    - TOP: y ≈ parent y, width >= 90% of parent width
    - BOTTOM: (y + height) ≈ (parent y + parent height), width >= 90% of parent width
    """
    results = []

    for parent_id, children in parent_index.items():
        parent = id_map.get(parent_id, {})
        parent_pos = parent.get("absolutePosition", {})
        parent_dim = parent.get("dimensions", {})
        parent_y = parent_pos.get("y", 0)
        parent_w = parent_dim.get("width", 0)
        parent_h = parent_dim.get("height", 0)

        if parent_w <= 0 or parent_h <= 0:
            continue

        for child in children:
            if child.get("type") not in ("INSTANCE", "FRAME", "GROUP", "CANVAS"):
                continue

            child_pos = child.get("absolutePosition", {})
            child_dim = child.get("dimensions", {})
            child_y = child_pos.get("y", 0)
            child_w = child_dim.get("width", 0)
            child_h = child_dim.get("height", 0)

            if child_w <= 0 or child_h <= 0:
                continue

            # Check if spans full width
            width_ratio = child_w / parent_w
            spans_full_width = width_ratio >= WIDTH_RATIO_THRESHOLD

            if not spans_full_width:
                continue

            # Determine position
            position = None
            rel_y = child_y - parent_y

            if abs(rel_y) <= POSITION_TOLERANCE_DP:
                position = "TOP"
            elif abs((rel_y + child_h) - parent_h) <= POSITION_TOLERANCE_DP:
                position = "BOTTOM"

            if position:
                # Collect descendant types for context
                child_types = _collect_descendant_types(child, id_map, max_depth=2)
                if not child_types:
                    continue

                results.append({
                    "node_id": child.get("id", ""),
                    "name": child.get("name", ""),
                    "position": position,
                    "spans_full_width": True,
                    "height": child_h,
                    "width_ratio": round(width_ratio, 2),
                    "contains_types": child_types,
                })

    logger.info("Detected %d positional anchors", len(results))
    return results


def detect_size_clusters(nodes: list[dict], parent_index: dict,
                          id_map: dict) -> list[dict]:
    """Detect siblings with same size, possibly forming a grid or repeated layout.

    Groups sibling nodes by (width, height) with tolerance, flags clusters of 3+.
    """
    results = []

    for parent_id, children in parent_index.items():
        if len(children) < MIN_REPEATING_COUNT:
            continue

        # Bucket children by rounded dimensions
        size_buckets = defaultdict(list)
        for child in children:
            dim = child.get("dimensions", {})
            w = round(dim.get("width", 0) / SIZE_CLUSTER_TOLERANCE) * SIZE_CLUSTER_TOLERANCE
            h = round(dim.get("height", 0) / SIZE_CLUSTER_TOLERANCE) * SIZE_CLUSTER_TOLERANCE
            size_buckets[(w, h)].append(child)

        for (w, h), members in size_buckets.items():
            if len(members) < MIN_REPEATING_COUNT or w == 0 or h == 0:
                continue

            # Check if children are arranged in a grid pattern
            xs = sorted(set(
                m.get("absolutePosition", {}).get("x", 0) for m in members
            ))
            ys = sorted(set(
                m.get("absolutePosition", {}).get("y", 0) for m in members
            ))
            is_grid = len(xs) > 1 and len(ys) > 1

            results.append({
                "cluster_width": w,
                "cluster_height": h,
                "member_count": len(members),
                "likely_grid_item": is_grid,
                "grid_columns": len(xs) if is_grid else 1,
                "parent_id": parent_id,
                "parent_name": id_map.get(parent_id, {}).get("name", ""),
            })

    logger.info("Detected %d size clusters", len(results))
    return results


def detect_scroll_candidates(nodes: list[dict], parent_index: dict,
                              id_map: dict) -> list[dict]:
    """Detect containers whose total children height exceeds the container height.

    These are candidates for ScrollView wrapping.
    """
    results = []

    for parent_id, children in parent_index.items():
        parent = id_map.get(parent_id, {})
        parent_dim = parent.get("dimensions", {})
        viewport_h = parent_dim.get("height", 0)

        if viewport_h <= 0 or len(children) < 2:
            continue

        # Calculate total content height from children's positions
        max_bottom = 0
        parent_y = parent.get("absolutePosition", {}).get("y", 0)
        for child in children:
            child_y = child.get("absolutePosition", {}).get("y", 0) - parent_y
            child_h = child.get("dimensions", {}).get("height", 0)
            max_bottom = max(max_bottom, child_y + child_h)

        ratio = max_bottom / viewport_h if viewport_h > 0 else 0

        if ratio >= SCROLL_RATIO_THRESHOLD:
            results.append({
                "node_id": parent_id,
                "name": parent.get("name", ""),
                "content_height": round(max_bottom),
                "viewport_height": round(viewport_h),
                "overflow_ratio": round(ratio, 2),
                "reason": f"content exceeds viewport by {ratio:.1f}x",
            })

    logger.info("Detected %d scroll candidates", len(results))
    return results


def detect_layout_spacing(nodes: list[dict], parent_index: dict,
                           id_map: dict) -> list[dict]:
    """Compute padding and sibling gaps for each parent container.

    For each parent with children, calculates:
    - padding: inset from parent edges to nearest child on each side
    - horizontal_gaps: gaps between horizontally adjacent siblings
    - vertical_gaps: gaps between vertically adjacent siblings
    - grid_gap: detected uniform gap for grid-like layouts

    Only emits entries where at least one spacing value exceeds
    SPACING_SIGNIFICANCE_DP to avoid noise.
    """
    results = []

    for parent_id, children in parent_index.items():
        if len(children) < 1 or len(children) > MAX_SPACING_CHILDREN:
            continue

        parent = id_map.get(parent_id, {})
        parent_dim = parent.get("dimensions", {})
        parent_pos = parent.get("absolutePosition", {})

        pw = parent_dim.get("width", 0)
        ph = parent_dim.get("height", 0)
        px = parent_pos.get("x", 0)
        py = parent_pos.get("y", 0)

        if pw <= 0 or ph <= 0:
            continue

        # -- Compute padding from parent edges to nearest child -----------
        child_positions = []
        for child in children:
            cp = child.get("absolutePosition", {})
            cd = child.get("dimensions", {})
            cx, cy = cp.get("x", 0), cp.get("y", 0)
            cw, ch = cd.get("width", 0), cd.get("height", 0)
            if cw > 0 and ch > 0:
                child_positions.append((cx, cy, cw, ch))

        if not child_positions:
            continue

        min_left = min(cx - px for cx, _, _, _ in child_positions)
        min_top = min(cy - py for _, cy, _, _ in child_positions)
        max_right = max(cx - px + cw for cx, _, cw, _ in child_positions)
        max_bottom = max(cy - py + ch for _, cy, _, ch in child_positions)

        padding = {
            "left": round(min_left),
            "top": round(min_top),
            "right": round(pw - max_right),
            "bottom": round(ph - max_bottom),
        }
        # Filter out 0 value padding keys to reduce verbose outputs
        padding = {k: v for k, v in padding.items() if v != 0}

        # -- Compute horizontal gaps (siblings in same row) ---------------
        # Sort children by x, group by overlapping y to find same-row peers
        horizontal_gaps = []
        sorted_by_x = sorted(child_positions, key=lambda c: c[0])
        for i in range(1, len(sorted_by_x)):
            prev_x, prev_y, prev_w, prev_h = sorted_by_x[i - 1]
            curr_x, curr_y, curr_w, curr_h = sorted_by_x[i]
            # Check if in same row (vertical overlap > 50%)
            overlap_top = max(prev_y, curr_y)
            overlap_bot = min(prev_y + prev_h, curr_y + curr_h)
            if overlap_bot - overlap_top > min(prev_h, curr_h) * 0.5:
                gap = round(curr_x - (prev_x + prev_w))
                if gap > 0:
                    horizontal_gaps.append(gap)

        # -- Compute vertical gaps (siblings in same column) --------------
        vertical_gaps = []
        sorted_by_y = sorted(child_positions, key=lambda c: c[1])
        for i in range(1, len(sorted_by_y)):
            prev_x, prev_y, prev_w, prev_h = sorted_by_y[i - 1]
            curr_x, curr_y, curr_w, curr_h = sorted_by_y[i]
            # Check if in same column (horizontal overlap > 50%)
            overlap_left = max(prev_x, curr_x)
            overlap_right = min(prev_x + prev_w, curr_x + curr_w)
            if overlap_right - overlap_left > min(prev_w, curr_w) * 0.5:
                gap = round(curr_y - (prev_y + prev_h))
                if gap > 0:
                    vertical_gaps.append(gap)

        # -- Detect uniform grid gap -------------------------------------
        all_gaps = horizontal_gaps + vertical_gaps
        grid_gap = None
        if len(all_gaps) >= 2:
            unique_gaps = set(all_gaps)
            # If all gaps are within tolerance, it's a uniform grid gap
            if len(unique_gaps) == 1 or (
                max(all_gaps) - min(all_gaps) <= SIZE_CLUSTER_TOLERANCE
            ):
                grid_gap = round(sum(all_gaps) / len(all_gaps))

        # Only emit if there's meaningful spacing data
        has_significant_padding = any(
            v >= SPACING_SIGNIFICANCE_DP for v in padding.values()
        )
        has_gaps = bool(horizontal_gaps or vertical_gaps)

        if has_significant_padding or has_gaps:
            entry = {
                "node_id": parent_id,
                "name": parent.get("name", ""),
                "dimensions": {"width": round(pw), "height": round(ph)},
                "padding": padding,
            }
            if horizontal_gaps:
                entry["horizontal_gaps"] = horizontal_gaps
            if vertical_gaps:
                entry["vertical_gaps"] = vertical_gaps
            if grid_gap is not None:
                entry["grid_gap"] = grid_gap
            results.append(entry)

    logger.info("Detected %d layout spacing entries", len(results))
    return results


def _parse_px_values(value: Any) -> list[float]:
    if value is None:
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    if not isinstance(value, str):
        return []
    parts = value.replace(",", " ").split()
    parsed = []
    for part in parts:
        cleaned = part.strip().removesuffix("px").removesuffix("dp")
        try:
            parsed.append(float(cleaned))
        except ValueError:
            continue
    return parsed


def _stroke_edges(value: Any) -> dict[str, float]:
    values = _parse_px_values(value)
    if not values:
        return {"top": 0, "right": 0, "bottom": 0, "left": 0}
    if len(values) == 1:
        top = right = bottom = left = values[0]
    elif len(values) == 2:
        top = bottom = values[0]
        right = left = values[1]
    elif len(values) == 3:
        top = values[0]
        right = left = values[1]
        bottom = values[2]
    else:
        top, right, bottom, left = values[:4]
    return {"top": top, "right": right, "bottom": bottom, "left": left}


def _find_divider(item: dict, parent_index: dict, id_map: dict) -> dict | None:
    item_dim = item.get("dimensions", {})
    item_w = item_dim.get("width", 0)
    item_h = item_dim.get("height", 0)
    for child in parent_index.get(item.get("id", ""), []):
        edges = _stroke_edges(child.get("strokeWidth"))
        if edges["bottom"] <= 0:
            continue
        child_dim = child.get("dimensions", {})
        child_w = child_dim.get("width", 0)
        child_h = child_dim.get("height", 0)
        same_size = (
            abs(child_w - item_w) <= SIZE_CLUSTER_TOLERANCE and
            abs(child_h - item_h) <= SIZE_CLUSTER_TOLERANCE
        )
        return {
            "kind": "bottom_stroke" if same_size else "stroke",
            "height": round(edges["bottom"]),
            "source_node": child.get("id", ""),
        }
    return None


def detect_list_metrics(nodes: list[dict], parent_index: dict, id_map: dict) -> list[dict]:
    """Detect repeat item dimensions, pitch, gaps, and divider ownership.

    This is separate from repeating_groups because a two-item preview list still
    has real list spacing that Mode B must preserve.
    """
    results = []

    for parent_id, children in parent_index.items():
        if len(children) < MIN_LIST_METRIC_COUNT or len(children) > MAX_SPACING_CHILDREN:
            continue

        groups = defaultdict(list)
        for child in children:
            dim = child.get("dimensions", {})
            w = round(dim.get("width", 0) / SIZE_CLUSTER_TOLERANCE) * SIZE_CLUSTER_TOLERANCE
            h = round(dim.get("height", 0) / SIZE_CLUSTER_TOLERANCE) * SIZE_CLUSTER_TOLERANCE
            if w <= 0 or h <= 0:
                continue
            groups[(_structure_hash(child, id_map), w, h)].append(child)

        parent = id_map.get(parent_id, {})
        parent_pos = parent.get("absolutePosition", {})
        px = parent_pos.get("x", 0)
        py = parent_pos.get("y", 0)

        for (_, bucket_w, bucket_h), group in groups.items():
            if len(group) < MIN_LIST_METRIC_COUNT:
                continue

            xs = [item.get("absolutePosition", {}).get("x", 0) for item in group]
            ys = [item.get("absolutePosition", {}).get("y", 0) for item in group]
            same_column = max(xs) - min(xs) <= POSITION_TOLERANCE_DP
            same_row = max(ys) - min(ys) <= POSITION_TOLERANCE_DP
            if not same_column and not same_row:
                continue

            axis = "vertical" if same_column else "horizontal"
            sorted_items = sorted(
                group,
                key=lambda item: item.get("absolutePosition", {}).get("y" if axis == "vertical" else "x", 0)
            )

            pitches = []
            gaps = []
            for prev, curr in zip(sorted_items, sorted_items[1:]):
                prev_pos = prev.get("absolutePosition", {})
                curr_pos = curr.get("absolutePosition", {})
                prev_dim = prev.get("dimensions", {})
                if axis == "vertical":
                    pitch = curr_pos.get("y", 0) - prev_pos.get("y", 0)
                    gap = curr_pos.get("y", 0) - (prev_pos.get("y", 0) + prev_dim.get("height", 0))
                else:
                    pitch = curr_pos.get("x", 0) - prev_pos.get("x", 0)
                    gap = curr_pos.get("x", 0) - (prev_pos.get("x", 0) + prev_dim.get("width", 0))
                pitches.append(round(pitch))
                gaps.append(round(gap))

            if not gaps or max(gaps) < SPACING_SIGNIFICANCE_DP:
                continue

            uniform_gap = max(gaps) - min(gaps) <= SIZE_CLUSTER_TOLERANCE
            uniform_pitch = max(pitches) - min(pitches) <= SIZE_CLUSTER_TOLERANCE
            sample = sorted_items[0]
            sample_dim = sample.get("dimensions", {})
            entry = {
                "container_id": parent_id,
                "container_name": parent.get("name", ""),
                "item_count": len(sorted_items),
                "axis": axis,
                "item_width": round(sample_dim.get("width", bucket_w)),
                "item_height": round(sample_dim.get("height", bucket_h)),
                "item_pitch": pitches[0] if uniform_pitch else None,
                "item_pitches": pitches,
                "item_gap": gaps[0] if uniform_gap else None,
                "item_gaps": gaps,
            }
            divider = _find_divider(sample, parent_index, id_map)
            if divider:
                entry["divider"] = divider
            results.append(entry)

    logger.info("Detected %d list metric entries", len(results))
    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_descendant_types(node: dict, id_map: dict, max_depth: int = 2,
                               _depth: int = 0) -> list[str]:
    """Collect node types of descendants up to max_depth."""
    if _depth > max_depth:
        return []

    types = []
    for cid in node.get("childIds", []):
        child = id_map.get(cid, {})
        child_type = child.get("type", "")
        if child_type:
            types.append(child_type)
        types.extend(_collect_descendant_types(child, id_map, max_depth, _depth + 1))

    return types


# ---------------------------------------------------------------------------
# Main Analysis
# ---------------------------------------------------------------------------

def analyze_structure(node_tree: dict) -> dict:
    """Run all structural analysis passes on a normalized node tree.

    Args:
        node_tree: Output of normalize_figma.py (has 'nodes' list).

    Returns:
        Structural hints dict with analysis results.
    """
    normalized = _normalize_input_tree(node_tree)
    nodes = normalized.get("nodes", [])
    if not nodes:
        logger.warning("No nodes found in node_tree")
        return {"repeating_groups": [], "positional_anchors": [],
                "size_clusters": [], "scroll_candidates": [],
                "layout_spacing": [], "list_metrics": []}

    parent_index, id_map = _build_child_index(nodes)

    raw_repeating = detect_repeating_siblings(nodes, parent_index, id_map)
    raw_anchors = detect_positional_anchors(nodes, parent_index, id_map)
    raw_scroll = detect_scroll_candidates(nodes, parent_index, id_map)
    raw_list = detect_list_metrics(nodes, parent_index, id_map)

    # Post-process repeating groups to keep only structure and ID
    pruned_repeating = []
    for g in raw_repeating:
        child_types = g.get("sample_child", {}).get("child_types", [])
        t = "dynamic_list" if "TEXT" in child_types or "INSTANCE" in child_types else "static_group"
        pruned_repeating.append({
            "parent_node_id": g["parent_node_id"],
            "parent_name": g["parent_name"],
            "type": t
        })

    # Post-process positional anchors to keep only structure and ID
    pruned_anchors = []
    for a in raw_anchors:
        pruned_anchors.append({
            "node_id": a["node_id"],
            "name": a["name"],
            "position": a["position"]
        })

    # Post-process scroll candidates to keep only structure and ID
    pruned_scroll = []
    for sc in raw_scroll:
        pruned_scroll.append({
            "node_id": sc["node_id"],
            "name": sc["name"]
        })

    # Post-process list metrics to keep only structure and ID
    pruned_list = []
    for lm in raw_list:
        pruned_list.append({
            "container_id": lm["container_id"],
            "container_name": lm["container_name"],
            "axis": lm["axis"]
        })

    return {
        "repeating_groups": pruned_repeating,
        "positional_anchors": pruned_anchors,
        "size_clusters": [],
        "scroll_candidates": pruned_scroll,
        "layout_spacing": [],
        "list_metrics": pruned_list,
        "metadata": {
            "total_nodes_analyzed": len(nodes),
            "total_parents_with_children": len(parent_index),
        },
    }


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        print("Usage: python analyze_structure.py <node_tree.json> <output_structural_hints.json>")
        sys.exit(1)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            node_tree = json.load(f)

        hints = analyze_structure(node_tree)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(hints, f, indent=2, ensure_ascii=False)

        summary = {
            "status": "success",
            "output_file": output_path,
            "repeating_groups": len(hints["repeating_groups"]),
            "positional_anchors": len(hints["positional_anchors"]),
            "size_clusters": len(hints["size_clusters"]),
            "layout_spacing": len(hints["layout_spacing"]),
            "scroll_candidates": len(hints["scroll_candidates"]),
        }
        print(json.dumps(summary, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
