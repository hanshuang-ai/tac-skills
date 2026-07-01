#!/usr/bin/env python3
"""
validate_handoff.py -- Pre-flight check for Mode B (Renderer).

Validates that all required Phase A+B artifacts exist in the work directory
and are structurally valid before starting code generation.

Usage:
    python validate_handoff.py <work_dir>

Exit codes:
    0 = ALL PASS (safe to proceed)
    1 = FAIL (missing or invalid critical artifacts)
    2 = WARN (non-critical issues, can proceed with limitations)
"""

import json
import os
import re
import sys


VALID_CHROME_EDGES = {"top", "bottom", "left", "right"}
BOUNDS_KEYS = ("x", "y", "width", "height")
GEOMETRY_TOLERANCE = 1.0


def check_file_exists(work_dir: str, filename: str) -> dict:
    """Check if a file exists and has non-trivial size."""
    path = os.path.join(work_dir, filename)
    if not os.path.exists(path):
        return {"file": filename, "status": "MISSING", "detail": "File not found"}
    size = os.path.getsize(path)
    if size < 10:
        return {"file": filename, "status": "EMPTY", "detail": f"File is suspiciously small ({size} bytes)"}
    return {"file": filename, "status": "OK", "size": size}


def validate_json(work_dir: str, filename: str) -> dict:
    """Check if a file is valid JSON and return parsed content."""
    path = os.path.join(work_dir, filename)
    if not os.path.exists(path):
        return {"file": filename, "status": "MISSING", "detail": "File not found", "data": None}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"file": filename, "status": "OK", "data": data}
    except json.JSONDecodeError as e:
        return {"file": filename, "status": "INVALID_JSON", "detail": str(e), "data": None}



def _load_optional_json(work_dir: str | None, filename: str):
    if not work_dir:
        return None
    path = os.path.join(work_dir, filename)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _skeleton_root(skeleton_data):
    if not isinstance(skeleton_data, dict):
        return None
    return skeleton_data.get("skeleton") or skeleton_data


def _collect_skeleton_ids_and_ancestors(skeleton_data):
    root = _skeleton_root(skeleton_data)
    ids = set()
    parent = {}
    ancestors = {}

    def walk(node, parent_id=None, ancestor_list=None):
        if not isinstance(node, dict):
            return
        node_id = node.get("id")
        if not node_id:
            return
        ancestor_list = list(ancestor_list or [])
        ids.add(node_id)
        parent[node_id] = parent_id
        ancestors[node_id] = list(ancestor_list)
        for child in node.get("ch", []) or []:
            walk(child, node_id, ancestor_list + [node_id])

    if root:
        walk(root)
    return ids, parent, ancestors


def _collect_raw_bounds(mastergo_data):
    """Return node_id -> raw/parent-relative bounds from mastergo_raw.json."""
    result = {}
    if not isinstance(mastergo_data, dict):
        return result
    roots = mastergo_data.get("dsl", {}).get("nodes") or mastergo_data.get("nodes") or []

    def walk(node, abs_x=0.0, abs_y=0.0):
        if not isinstance(node, dict):
            return
        style = node.get("layoutStyle") or {}
        x = style.get("relativeX", 0) or 0
        y = style.get("relativeY", 0) or 0
        w = style.get("width")
        h = style.get("height")
        node_id = node.get("id")
        raw_x = abs_x + x
        raw_y = abs_y + y
        if node_id and w is not None and h is not None:
            result[node_id] = {
                "raw": {"x": raw_x, "y": raw_y, "width": w, "height": h},
                "parent_relative": {"x": x, "y": y, "width": w, "height": h},
            }
        for child in node.get("children", []) or []:
            walk(child, raw_x, raw_y)

    for root in roots:
        walk(root)
    return result


def _valid_bound(bound) -> bool:
    return isinstance(bound, dict) and all(_is_number(bound.get(k)) for k in BOUNDS_KEYS)


def _compare_bounds(actual: dict, expected: dict, tolerance: float = GEOMETRY_TOLERANCE):
    diffs = []
    if not _valid_bound(actual) or not _valid_bound(expected):
        return ["invalid"]
    for key in BOUNDS_KEYS:
        if abs(float(actual[key]) - float(expected[key])) > tolerance:
            diffs.append(f"{key}: got {actual[key]}, expected {expected[key]}")
    return diffs


def _validate_blueprint_geometry(nodes_by_level, raw_bounds, coordinate_normalization):
    issues = []
    offsets = coordinate_normalization if isinstance(coordinate_normalization, dict) else {}
    top = offsets.get("top", 0) if _is_number(offsets.get("top", 0)) else 0
    left = offsets.get("left", 0) if _is_number(offsets.get("left", 0)) else 0

    for depth, node in nodes_by_level:
        node_id = node.get("id", "?")
        if node.get("type") == "system_component" and node.get("exclude_from_layout") is True:
            require_normalized = False
        elif node.get("role") == "root":
            require_normalized = False
        else:
            require_normalized = depth == 0 and (top > 0 or left > 0)

        bounds = node.get("bounds")
        if not isinstance(bounds, dict):
            issues.append(f"CRITICAL: Node '{node_id}' is missing machine-readable 'bounds'")
            continue
        if not _valid_bound(bounds.get("raw")):
            issues.append(f"CRITICAL: Node '{node_id}' bounds.raw is missing or invalid")
        if not _valid_bound(bounds.get("parent_relative")):
            issues.append(f"CRITICAL: Node '{node_id}' bounds.parent_relative is missing or invalid")
        if require_normalized and not _valid_bound(bounds.get("normalized")):
            issues.append(f"CRITICAL: Node '{node_id}' must include bounds.normalized after chrome normalization")

        expected = raw_bounds.get(node_id)
        if expected:
            raw_diffs = _compare_bounds(bounds.get("raw"), expected["raw"])
            if raw_diffs:
                issues.append(f"CRITICAL: Node '{node_id}' bounds.raw does not match DSL ({'; '.join(raw_diffs)})")
            rel_diffs = _compare_bounds(bounds.get("parent_relative"), expected["parent_relative"])
            if rel_diffs:
                issues.append(f"CRITICAL: Node '{node_id}' bounds.parent_relative does not match DSL ({'; '.join(rel_diffs)})")

        if require_normalized and _valid_bound(bounds.get("raw")) and _valid_bound(bounds.get("normalized")):
            expected_norm = dict(bounds["raw"])
            expected_norm["x"] = expected_norm["x"] - left
            expected_norm["y"] = expected_norm["y"] - top
            norm_diffs = _compare_bounds(bounds.get("normalized"), expected_norm)
            if norm_diffs:
                issues.append(
                    f"CRITICAL: Node '{node_id}' bounds.normalized must equal raw minus chrome offsets "
                    f"({'; '.join(norm_diffs)})"
                )

    return issues


def _collect_list_metric_refs(data: dict):
    refs = []
    for level in data.get("levels", []) or []:
        depth = level.get("depth", "?")
        for node in level.get("nodes", []) or []:
            ref = node.get("list_metrics_ref")
            if ref:
                refs.append((f"node {node.get('id', '?')} depth={depth}", ref, node.get("list_metrics_override")))
        for group_key in ("repeating_groups",):
            for group in level.get(group_key, []) or []:
                ref = group.get("list_metrics_ref")
                if ref:
                    refs.append((f"{group_key} at depth={depth}", ref, group.get("list_metrics_override")))
    return refs


def _validate_list_metric_refs(data: dict, structural_hints: dict | None):
    issues = []
    metrics = (structural_hints or {}).get("list_metrics") or []
    valid_refs = {m.get("container_id") for m in metrics if isinstance(m, dict) and m.get("container_id")}
    for owner, ref, _override in _collect_list_metric_refs(data):
        if ref not in valid_refs:
            issues.append(
                f"CRITICAL: {owner} list_metrics_ref '{ref}' does not match any "
                "structural_hints.json.list_metrics[].container_id"
            )
    return issues


def _validate_coverage_and_terminals(data: dict, skeleton_data: dict | None):
    issues = []
    skeleton_ids, _parents, ancestors = _collect_skeleton_ids_and_ancestors(skeleton_data)
    if not skeleton_ids:
        return issues

    emitted = []
    emitted_set = set()
    node_by_id = {}
    for level in data.get("levels", []) or []:
        for node in level.get("nodes", []) or []:
            node_id = node.get("id")
            if node_id:
                emitted.append(node_id)
                emitted_set.add(node_id)
                node_by_id[node_id] = node

    coverage_count = {sid: 0 for sid in skeleton_ids}
    for node_id in emitted_set:
        if node_id in coverage_count:
            coverage_count[node_id] += 1

    for node_id, node in node_by_id.items():
        coverage = node.get("coverage") or {}
        covered = coverage.get("covered_subtree_ids") or []
        if node.get("terminal") or node.get("exclude_from_layout") or covered:
            if not isinstance(coverage, dict) or not coverage.get("mode"):
                issues.append(f"CRITICAL: Node '{node_id}' must declare coverage.mode")
            if not isinstance(covered, list):
                issues.append(f"CRITICAL: Node '{node_id}' coverage.covered_subtree_ids must be an array")
                continue
        if not isinstance(covered, list):
            continue
        for covered_id in covered:
            if covered_id not in skeleton_ids:
                issues.append(f"CRITICAL: Node '{node_id}' covers unknown skeleton id '{covered_id}'")
                continue
            if node_id not in ancestors.get(covered_id, []) and node_id != covered_id:
                issues.append(f"CRITICAL: Node '{node_id}' covers non-descendant skeleton id '{covered_id}'")
            coverage_count[covered_id] += 1

    missing = sorted([sid for sid, count in coverage_count.items() if count == 0])
    duplicated = sorted([sid for sid, count in coverage_count.items() if count > 1])
    if missing:
        preview = ", ".join(missing[:10])
        issues.append(f"CRITICAL: Blueprint coverage missing {len(missing)} skeleton nodes (first: {preview})")
    if duplicated:
        preview = ", ".join(duplicated[:10])
        issues.append(f"CRITICAL: Blueprint coverage duplicates {len(duplicated)} skeleton nodes (first: {preview})")

    terminal_ids = {node_id for node_id, node in node_by_id.items() if node.get("terminal")}
    for node_id in emitted_set:
        for ancestor_id in ancestors.get(node_id, []):
            if ancestor_id in terminal_ids:
                issues.append(f"CRITICAL: Terminal node '{ancestor_id}' has emitted descendant '{node_id}'")
                break

    return issues

def validate_blueprint(data: dict, work_dir: str | None = None) -> list:
    """Validate recursive_blueprint.json structural integrity and DSL alignment."""
    issues = []

    # Check file_id
    file_id = data.get("file_id")
    if not file_id:
        issues.append("CRITICAL: 'file_id' is missing from blueprint")

    # Check levels array
    levels = data.get("levels")
    if not levels or not isinstance(levels, list):
        issues.append("CRITICAL: 'levels' array is missing or empty")
        return issues

    # Collect all node IDs and check for duplicates
    all_node_ids = []
    excluded_chrome_nodes = []
    depth_zero_renderable_nodes = []
    for level in levels:
        depth = level.get("depth", "?")
        nodes = level.get("nodes", [])
        if not nodes:
            issues.append(f"WARNING: Level depth={depth} has no nodes")
            continue
        for node in nodes:
            node_id = node.get("id")
            if not node_id:
                issues.append(f"CRITICAL: Node at depth={depth} has no 'id'")
                continue
            # Validate ID format (should be like "22:34698")
            if not re.match(r"^\d+:\d+$", node_id):
                issues.append(f"WARNING: Node ID '{node_id}' has unexpected format (expected 'XX:XXXXX')")
            if node_id in all_node_ids:
                issues.append(f"CRITICAL: Duplicate node ID '{node_id}' found")
            all_node_ids.append(node_id)

            # Check for unresolved human review
            if node.get("needs_human_review"):
                issues.append(f"CRITICAL: Node '{node_id}' ({node.get('name', '?')}) has unresolved needs_human_review=true")

            is_excluded_chrome = (
                node.get("type") == "system_component"
                and node.get("exclude_from_layout") is True
            )
            if is_excluded_chrome:
                excluded_chrome_nodes.append(node)
            elif depth == 0:
                depth_zero_renderable_nodes.append(node)

    if not all_node_ids:
        issues.append("CRITICAL: No nodes found in blueprint")

    issues.extend(
        validate_chrome_coordinate_contract(
            data.get("coordinate_normalization"),
            excluded_chrome_nodes,
            depth_zero_renderable_nodes,
        )
    )

    if work_dir:
        nodes_by_level = [
            (level.get("depth", "?"), node)
            for level in levels
            for node in level.get("nodes", [])
        ]
        skeleton_data = _load_optional_json(work_dir, "skeleton_tree.json")
        structural_hints = _load_optional_json(work_dir, "structural_hints.json")
        mastergo_data = _load_optional_json(work_dir, "mastergo_raw.json")

        issues.extend(_validate_coverage_and_terminals(data, skeleton_data))
        issues.extend(_validate_list_metric_refs(data, structural_hints))
        raw_bounds = _collect_raw_bounds(mastergo_data)
        if raw_bounds:
            issues.extend(
                _validate_blueprint_geometry(
                    nodes_by_level,
                    raw_bounds,
                    data.get("coordinate_normalization"),
                )
            )
        else:
            issues.append("WARNING: mastergo_raw.json bounds unavailable; skipped DSL geometry cross-check")

    return issues


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_chrome_coordinate_contract(
    coordinate_normalization,
    excluded_chrome_nodes: list,
    depth_zero_renderable_nodes: list,
) -> list:
    """Validate system chrome exclusion and root coordinate normalization."""
    issues = []

    if not excluded_chrome_nodes:
        return issues

    if not isinstance(coordinate_normalization, dict):
        return ["CRITICAL: Excluded system chrome exists but 'coordinate_normalization' is missing or invalid"]

    offsets = {}
    for edge in VALID_CHROME_EDGES:
        value = coordinate_normalization.get(edge, 0)
        if not _is_number(value) or value < 0:
            issues.append(f"CRITICAL: coordinate_normalization.{edge} must be a non-negative number")
            value = 0
        offsets[edge] = value

    if not any(offsets.values()):
        issues.append("CRITICAL: Excluded system chrome exists but all coordinate_normalization offsets are 0")

    if coordinate_normalization.get("applied_at") != "root_renderable_children":
        issues.append("CRITICAL: coordinate_normalization.applied_at must be 'root_renderable_children'")

    for node in excluded_chrome_nodes:
        node_id = node.get("id", "?")
        if node.get("coordinate_space") != "excluded_system_chrome":
            issues.append(
                f"CRITICAL: Excluded chrome node '{node_id}' must set coordinate_space='excluded_system_chrome'"
            )

        edge = node.get("system_chrome_edge")
        if edge not in VALID_CHROME_EDGES:
            issues.append(
                f"CRITICAL: Excluded chrome node '{node_id}' must set system_chrome_edge to one of {sorted(VALID_CHROME_EDGES)}"
            )
            continue

        contribution = node.get("normalization_contribution")
        if not _is_number(contribution) or contribution <= 0:
            issues.append(
                f"CRITICAL: Excluded chrome node '{node_id}' must set a positive normalization_contribution"
            )
            continue

        if offsets.get(edge, 0) < contribution:
            issues.append(
                f"CRITICAL: coordinate_normalization.{edge} ({offsets.get(edge, 0)}) is smaller than "
                f"chrome node '{node_id}' contribution ({contribution})"
            )

    if offsets.get("top", 0) > 0 or offsets.get("left", 0) > 0:
        for node in depth_zero_renderable_nodes:
            if node.get("coordinate_space") != "root_normalized":
                issues.append(
                    f"CRITICAL: Depth-0 renderable node '{node.get('id', '?')}' must set "
                    "coordinate_space='root_normalized' when top/left chrome offsets are excluded"
                )

    return issues


def validate_file_context(data: dict) -> list:
    """Validate file_context metadata has required fields."""
    issues = []
    if not data.get("fileId"):
        issues.append("CRITICAL: 'fileId' is missing from file_context metadata")
    if not data.get("rootLayerId"):
        issues.append("WARNING: 'rootLayerId' is missing from file_context metadata")
    return issues


def validate_user_decisions(data: dict) -> list:
    """Validate optional user_decisions.json contains only authoritative external decisions."""
    issues = []

    if data.get("version") != 1:
        issues.append("WARNING: user_decisions.json should use version=1")

    status = data.get("status")
    if status and status not in {"resolved", "complete"}:
        issues.append("WARNING: user_decisions.json status should be 'resolved' or 'complete' when present")

    items = data.get("items")
    if items is None:
        issues.append("CRITICAL: user_decisions.json is missing 'items'")
        return issues
    if not isinstance(items, list):
        issues.append("CRITICAL: user_decisions.json 'items' must be an array")
        return issues

    valid_sources = {"user", "script", "workflow_default"}
    seen_ids = set()

    for index, item in enumerate(items):
        item_id = item.get("id") or f"index {index}"
        if not item.get("id"):
            issues.append(f"CRITICAL: user_decisions item at index {index} has no id")
        elif item_id in seen_ids:
            issues.append(f"CRITICAL: Duplicate user_decisions id '{item_id}'")
        seen_ids.add(item_id)

        source = item.get("source")
        if source == "llm":
            issues.append(f"CRITICAL: user_decisions item '{item_id}' uses forbidden source 'llm'")
        elif source not in valid_sources:
            issues.append(f"CRITICAL: user_decisions item '{item_id}' has invalid source '{source}'")

        if not item.get("decision"):
            issues.append(f"CRITICAL: user_decisions item '{item_id}' has no decision")

        node_ids = item.get("node_ids", [])
        if node_ids is not None and not isinstance(node_ids, list):
            issues.append(f"WARNING: user_decisions item '{item_id}' node_ids should be an array")

        if not item.get("impact"):
            issues.append(f"WARNING: user_decisions item '{item_id}' has no impact description")

    return issues


def _has_ref(value) -> bool:
    return isinstance(value, dict) and bool(value.get("artifact")) and (
        bool(value.get("json_pointer")) or bool(value.get("node_id")) or bool(value.get("decision_id"))
    )


def validate_handoff_facts(data: dict) -> list:
    """Validate canonical handoff excerpt index required by Mode A docs and Mode B."""
    issues = []

    if data.get("version") != 2:
        issues.append("WARNING: handoff_facts.json should use version=2 for excerpt-index format")
    if data.get("kind") != "handoff_excerpt_index":
        issues.append("CRITICAL: handoff_facts.json kind must be 'handoff_excerpt_index'")
    if data.get("source_of_truth") is not True:
        issues.append("WARNING: handoff_facts.json should set source_of_truth=true")

    source_artifacts = data.get("source_artifacts")
    if not isinstance(source_artifacts, dict) or not source_artifacts.get("blueprint"):
        issues.append("CRITICAL: handoff_facts.json missing source_artifacts.blueprint")

    scope = data.get("confirmed_render_scope")
    if not isinstance(scope, dict):
        issues.append("CRITICAL: handoff_facts.json missing confirmed_render_scope object")
    else:
        if not _has_ref(scope.get("decision_ref")):
            issues.append("CRITICAL: confirmed_render_scope.decision_ref must reference user_decisions.json")
        if not scope.get("selected_module_refs") and not scope.get("excluded_module_refs"):
            issues.append("CRITICAL: confirmed_render_scope must include selected_module_refs or excluded_module_refs")
        if not scope.get("downstream_rule"):
            issues.append("WARNING: confirmed_render_scope should describe downstream reasoning rule")

    coordinate_refs = data.get("coordinate_policy_refs")
    if not isinstance(coordinate_refs, dict):
        issues.append("CRITICAL: handoff_facts.json missing coordinate_policy_refs object")
    else:
        if not _has_ref(coordinate_refs.get("normalization_ref")):
            issues.append("CRITICAL: coordinate_policy_refs.normalization_ref must reference recursive_blueprint.json")
        key_bounds_refs = coordinate_refs.get("key_bounds_refs")
        if not isinstance(key_bounds_refs, list) or not key_bounds_refs:
            issues.append("WARNING: coordinate_policy_refs.key_bounds_refs should contain key bounds references")

    module_index = data.get("module_index")
    if not isinstance(module_index, list) or not module_index:
        issues.append("CRITICAL: handoff_facts.json module_index must be a non-empty array")
    else:
        for index, module in enumerate(module_index):
            module_id = module.get("node_id") or f"index {index}"
            if not module.get("node_id"):
                issues.append(f"CRITICAL: module_index item at index {index} has no node_id")
            if "included_in_render_scope" not in module:
                issues.append(f"CRITICAL: module_index item '{module_id}' missing included_in_render_scope")
            if not _has_ref(module.get("blueprint_ref")):
                issues.append(f"CRITICAL: module_index item '{module_id}' missing blueprint_ref")
            if not isinstance(module.get("bounds_ref"), dict):
                issues.append(f"WARNING: module_index item '{module_id}' missing bounds_ref")

    summary_view = data.get("summary_view")
    if not isinstance(summary_view, dict):
        issues.append("CRITICAL: handoff_facts.json missing summary_view object")
    else:
        required_summary_sections = [
            "page_structure",
            "ascii_diagram",
            "decisions",
            "controls_and_styles",
            "implementation_plan",
            "pending_user_confirmations",
        ]
        for section in required_summary_sections:
            value = summary_view.get(section)
            if not isinstance(value, dict) or not value.get("text"):
                issues.append(f"CRITICAL: summary_view.{section}.text is missing")
            elif section != "pending_user_confirmations" and not isinstance(value.get("supporting_refs"), list):
                issues.append(f"WARNING: summary_view.{section}.supporting_refs should be an array")

    mode_b_contract = data.get("mode_b_contract")
    if not isinstance(mode_b_contract, dict):
        issues.append("CRITICAL: handoff_facts.json missing mode_b_contract object")
    else:
        must_read_refs = mode_b_contract.get("must_read_refs")
        has_handoff_ref = any(
            isinstance(item, dict) and item.get("artifact") == "handoff_facts.json"
            for item in (must_read_refs or [])
        )
        if not isinstance(must_read_refs, list) or not has_handoff_ref:
            issues.append("CRITICAL: mode_b_contract.must_read_refs must include handoff_facts.json")
        must_not = mode_b_contract.get("must_not_reinterpret")
        if not isinstance(must_not, list) or not must_not:
            issues.append("WARNING: mode_b_contract.must_not_reinterpret should list frozen conclusions")

    return issues


def validate_render_plan(work_dir: str) -> dict:
    """Validate render_plan.md only when present. Mode A no longer requires it."""
    path = os.path.join(work_dir, "render_plan.md")
    if not os.path.exists(path):
        return {"status": "OPTIONAL_MISSING", "detail": "render_plan.md not generated in Mode A; Mode B will create it before coding", "issues": []}

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    issues = []
    size = len(content)

    # Check required sections (by heading)
    required_sections = [
        ("User / Workflow Decisions", "Section 0"),
        ("Layout Reuse Strategy", "Section 1"),
        ("Special Rendering / Edge Cases", "Section 2"),
        ("High-Level Task Checklist", "Section 3"),
    ]

    for keyword, section_name in required_sections:
        if keyword.lower() not in content.lower():
            issues.append(f"WARNING: {section_name} ('{keyword}') not found in render_plan.md")

    # Check for TODO items in task checklist. Pre-coding render plans must not claim
    # implementation work is already done.
    todo_count = content.count("- [ ]")
    done_count = content.count("- [x]")
    in_progress_count = content.count("- [/]")
    if done_count > 0 or in_progress_count > 0:
        issues.append(
            f"CRITICAL: Pre-coding render_plan.md must use unchecked TODO boxes only "
            f"(found {done_count} done, {in_progress_count} in-progress)"
        )
    mode_b_completion_patterns = [
        r"(?i)lint\s+(check\s+)?(all\s+)?pass",
        r"(?i)generated\s+(layout|xml|resources|adapter)",
        r"已生成",
        r"校验通过",
    ]
    for pattern in mode_b_completion_patterns:
        if re.search(pattern, content):
            issues.append(
                "CRITICAL: Pre-coding render_plan.md contains implementation completion wording; "
                "it must describe upcoming rendering tasks only"
            )
            break

    # Check for suspicious default values that may indicate fabricated data
    suspicious_patterns = [
        (r'\b16dp\b', "16dp (common LLM default)"),
        (r'\b8dp\b', "8dp (common LLM default)"),
        (r'#333333\b', "#333333 (common LLM default)"),
        (r'#666666\b', "#666666 (common LLM default)"),
    ]
    fabrication_warnings = []
    for pattern, desc in suspicious_patterns:
        matches = re.findall(pattern, content)
        if len(matches) > 3:  # Allow a few, flag if many
            fabrication_warnings.append(f"SUSPECT: {desc} appears {len(matches)} times -- verify against DSL")

    return {
        "status": "OK" if not any(i.startswith("CRITICAL") for i in issues) else "FAIL",
        "size": size,
        "todo_count": todo_count,
        "done_count": done_count,
        "in_progress_count": in_progress_count,
        "issues": issues,
        "fabrication_warnings": fabrication_warnings,
    }


def validate_mode_a_user_docs(work_dir: str) -> dict:
    """Validate human-facing Mode A handoff prompt. Summary lives in handoff_facts.json.summary_view."""
    specs = {
        "handoff_prompt.md": [
            "handoff_facts.json",
            "Mode B 交接 Prompt",
            "工作目录",
            "请先读取这些文件",
            "必须遵守这些决策",
            "用户可指导修改的点",
            "validate_handoff.py",
        ],
    }
    issues = []
    sizes = {}

    for filename, required in specs.items():
        path = os.path.join(work_dir, filename)
        if not os.path.exists(path):
            issues.append(f"CRITICAL: {filename} is missing")
            continue
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        sizes[filename] = len(content)
        for keyword in required:
            if keyword.lower() not in content.lower():
                issues.append(f"CRITICAL: {filename} missing '{keyword}'")

    return {
        "status": "OK" if not any(i.startswith("CRITICAL") for i in issues) else "FAIL",
        "sizes": sizes,
        "issues": issues,
    }


def validate_page_ui_spec(work_dir: str, blueprint_data: dict | None) -> dict:
    """Validate optional page UI spec when present. Missing optional spec is OK."""
    issues = []
    sizes = {}

    if not blueprint_data:
        return {"status": "SKIPPED", "detail": "Blueprint unavailable; optional page UI spec validation skipped", "issues": issues, "sizes": sizes}

    levels = blueprint_data.get("levels", [])
    page_name = "page"
    for level in levels:
        if level.get("depth") == 0:
            nodes = level.get("nodes", [])
            if nodes:
                page_name = nodes[0].get("name", "page")
                break

    page_name_clean = re.sub(r'[\\/*?:"<>|]', "", page_name).strip()
    if not page_name_clean.endswith("页面"):
        target_filename = f"page_ui_spec_{page_name_clean}页面.md"
    else:
        target_filename = f"page_ui_spec_{page_name_clean}.md"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(script_dir))))

    design_baseline_ui_dir = os.path.join(project_root, "persistent-assets", "design", "_baseline", "ui")
    global_path = os.path.join(design_baseline_ui_dir, target_filename)

    if not os.path.exists(global_path):
        return {
            "status": "OPTIONAL_MISSING",
            "detail": f"Optional page UI spec not generated: persistent-assets/design/_baseline/ui/{target_filename}",
            "issues": issues,
            "sizes": sizes,
        }

    with open(global_path, "r", encoding="utf-8") as f:
        content = f.read()
    sizes[target_filename] = len(content)

    required_headings = [
        "handoff_facts.json",
        "页面 UI 规格说明书",
        "页面 UI 概述",
        "UI 细节规范",
        "颜色系统",
        "字体与排版样式",
        "交互控件与语义映射",
        "开发与验证指引",
    ]
    for heading in required_headings:
        if heading.lower() not in content.lower():
            issues.append(f"CRITICAL: {target_filename} is missing heading/content: '{heading}'")

    return {
        "status": "OK" if not any(i.startswith("CRITICAL") for i in issues) else "FAIL",
        "sizes": sizes,
        "issues": issues,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_handoff.py <work_dir>")
        sys.exit(1)

    work_dir = sys.argv[1]
    if not os.path.isdir(work_dir):
        print(f"FAIL: Work directory does not exist: {work_dir}")
        sys.exit(1)

    print(f"=== MasterGo Handoff Validation ===")
    print(f"Work directory: {os.path.abspath(work_dir)}")
    print()

    # --- CRITICAL files (must exist for Mode B) ---
    critical_files = [
        "recursive_blueprint.json",
        "handoff_facts.json",
        "pipeline_result.json",
        "handoff_prompt.md",
        "token_registry.json",
        "mastergo_raw.json",
    ]

    # --- OPTIONAL files (nice to have) ---
    optional_files = [
        "skeleton_tree.json",
        "structural_hints.json",
        "semantic_mapping.json",
    ]

    all_issues = []
    has_critical_failure = False

    # [1/7] Critical files
    print("[1/7] Checking critical files...")
    for fname in critical_files:
        result = check_file_exists(work_dir, fname)
        status_icon = "OK" if result["status"] == "OK" else "FAIL"
        detail = f" ({result.get('size', 0)} bytes)" if result["status"] == "OK" else f" -- {result.get('detail', '')}"
        print(f"  [{status_icon}] {fname}{detail}")
        if result["status"] != "OK":
            has_critical_failure = True
            all_issues.append(f"CRITICAL: {fname} -- {result.get('detail', 'unknown issue')}")

    # [2/7] Optional files
    print()
    print("[2/7] Checking optional files...")
    for fname in optional_files:
        result = check_file_exists(work_dir, fname)
        status_icon = "OK" if result["status"] == "OK" else "WARN"
        detail = f" ({result.get('size', 0)} bytes)" if result["status"] == "OK" else f" -- {result.get('detail', '')}"
        print(f"  [{status_icon}] {fname}{detail}")
        if result["status"] != "OK":
            all_issues.append(f"WARNING: {fname} -- {result.get('detail', 'unknown issue')}")

    # [3/7] Blueprint validation
    print()
    print("[3/7] Validating recursive_blueprint.json structure...")
    bp_result = validate_json(work_dir, "recursive_blueprint.json")
    if bp_result["status"] == "OK" and bp_result["data"]:
        bp_issues = validate_blueprint(bp_result["data"], work_dir)
        for issue in bp_issues:
            print(f"  {issue}")
            all_issues.append(issue)
            if issue.startswith("CRITICAL"):
                has_critical_failure = True
        if not bp_issues:
            levels = bp_result["data"].get("levels", [])
            total_nodes = sum(len(l.get("nodes", [])) for l in levels)
            terminal_nodes = sum(
                1 for l in levels for n in l.get("nodes", []) if n.get("terminal")
            )
            dynamic_nodes = sum(
                1 for l in levels for n in l.get("nodes", [])
                if n.get("data_binding") == "dynamic"
            )
            print(f"  [OK] Blueprint valid: {total_nodes} nodes, {len(levels)} levels")
            print(f"       Terminal: {terminal_nodes}, Dynamic: {dynamic_nodes}")
    elif bp_result["status"] != "MISSING":
        print(f"  [FAIL] {bp_result.get('detail', 'Invalid JSON')}")
        has_critical_failure = True

    # [4/7] File context validation (from pipeline_result.json)
    print()
    print("[4/7] Validating file_context within pipeline_result.json...")
    pr_result = validate_json(work_dir, "pipeline_result.json")
    if pr_result["status"] == "OK" and pr_result["data"]:
        file_context_data = pr_result["data"].get("file_context")
        if not file_context_data:
            print("  [FAIL] 'file_context' object is missing from pipeline_result.json")
            has_critical_failure = True
            all_issues.append("CRITICAL: 'file_context' object is missing from pipeline_result.json")
        else:
            fc_issues = validate_file_context(file_context_data)
            for issue in fc_issues:
                print(f"  {issue}")
                all_issues.append(issue)
                if issue.startswith("CRITICAL"):
                    has_critical_failure = True
            if not fc_issues:
                print(f"  [OK] fileId={file_context_data.get('fileId')}")
    elif pr_result["status"] != "MISSING":
        print(f"  [FAIL] {pr_result.get('detail', 'Invalid JSON')}")
        has_critical_failure = True

    # [5/7] Optional user/workflow decisions validation
    print()
    print("[5/7] Validating optional user_decisions.json...")
    ud_result = validate_json(work_dir, "user_decisions.json")
    if ud_result["status"] == "OK" and ud_result["data"] is not None:
        ud_issues = validate_user_decisions(ud_result["data"])
        for issue in ud_issues:
            print(f"  {issue}")
            all_issues.append(issue)
            if issue.startswith("CRITICAL"):
                has_critical_failure = True
        if not ud_issues:
            items = ud_result["data"].get("items", [])
            print(f"  [OK] user_decisions.json valid: {len(items)} persisted decisions")
    elif ud_result["status"] == "MISSING":
        print("  [OK] user_decisions.json not present; no persisted external decisions")
    else:
        print(f"  [FAIL] {ud_result.get('detail', 'Invalid JSON')}")
        has_critical_failure = True

    # [5.5/7] Canonical handoff facts validation
    print()
    print("[5.5/7] Validating handoff_facts.json canonical facts...")
    hf_result = validate_json(work_dir, "handoff_facts.json")
    if hf_result["status"] == "OK" and hf_result["data"] is not None:
        hf_issues = validate_handoff_facts(hf_result["data"])
        for issue in hf_issues:
            print(f"  {issue}")
            all_issues.append(issue)
            if issue.startswith("CRITICAL"):
                has_critical_failure = True
        if not hf_issues:
            modules = hf_result["data"].get("module_index", [])
            included = sum(1 for m in modules if m.get("included_in_render_scope") is True)
            print(f"  [OK] handoff_facts.json excerpt index valid: {included}/{len(modules)} modules included")
    elif hf_result["status"] == "MISSING":
        print("  [FAIL] handoff_facts.json is missing")
        has_critical_failure = True
        all_issues.append("CRITICAL: handoff_facts.json is missing")
    else:
        print(f"  [FAIL] {hf_result.get('detail', 'Invalid JSON')}")
        has_critical_failure = True

    # [6/7] Deprecated clarification artifact guard
    print()
    print("[6/7] Checking deprecated clarification artifacts...")
    deprecated_found = []
    for deprecated_name in ("clarification_candidates.json", "clarification_decisions.json"):
        deprecated_path = os.path.join(work_dir, deprecated_name)
        if os.path.exists(deprecated_path):
            deprecated_found.append(deprecated_name)
    if deprecated_found:
        warning = (
            "WARNING: Deprecated clarification artifacts are present and will be ignored: "
            + ", ".join(deprecated_found)
        )
        print(f"  {warning}")
        all_issues.append(warning)
    else:
        print("  [OK] No deprecated clarification artifacts present")

    print()
    print("[6.75/7] Validating Mode A user-facing docs...")
    user_docs_result = validate_mode_a_user_docs(work_dir)
    for issue in user_docs_result.get("issues", []):
        print(f"  {issue}")
        all_issues.append(issue)
        if issue.startswith("CRITICAL"):
            has_critical_failure = True
    if not user_docs_result.get("issues"):
        sizes = user_docs_result.get("sizes", {})
        print(
            "  [OK] Mode A user docs valid "
            f"(handoff_prompt.md={sizes.get('handoff_prompt.md', 0)} bytes; "
            "summary is stored in handoff_facts.json#summary_view)"
        )

    print()
    print("[6.8/7] Checking optional page UI spec project doc copy...")
    ui_spec_result = validate_page_ui_spec(
        work_dir,
        bp_result["data"] if bp_result["status"] == "OK" else None
    )
    if ui_spec_result.get("status") in {"OPTIONAL_MISSING", "SKIPPED"}:
        print(f"  [OK] {ui_spec_result.get('detail', 'Optional page UI spec not generated')}")
    else:
        for issue in ui_spec_result.get("issues", []):
            print(f"  {issue}")
            all_issues.append(issue)
            if issue.startswith("CRITICAL"):
                has_critical_failure = True
        if not ui_spec_result.get("issues"):
            ui_sizes = ui_spec_result.get("sizes", {})
            global_fname = next(iter(ui_sizes.keys()), "page_ui_spec_xxxx页面.md")
            global_sz = ui_sizes.get(global_fname, 0)
            print(
                "  [OK] Optional Page UI Spec valid "
                f"(global persistent-assets/design/_baseline/ui/{global_fname}={global_sz} bytes)"
            )

    # [7/7] Render plan note (Mode B artifact, not part of Mode A handoff)
    print()
    print("[7/7] Checking render_plan.md status...")
    rp_result = validate_render_plan(work_dir)
    if rp_result["status"] == "OPTIONAL_MISSING":
        print(f"  [OK] {rp_result.get('detail', 'render_plan.md will be generated in Mode B')}")
    else:
        print("  [INFO] render_plan.md exists, but it is a Mode B planning artifact and is not required for Mode A ALL PASS")
        for issue in rp_result.get("issues", []):
            print(f"  [INFO] {issue}")
        for warn in rp_result.get("fabrication_warnings", []):
            print(f"  [INFO] {warn}")
        if not rp_result.get("issues") and not rp_result.get("fabrication_warnings"):
            todo = rp_result.get("todo_count", 0)
            done = rp_result.get("done_count", 0)
            in_prog = rp_result.get("in_progress_count", 0)
            print(f"  [OK] Existing render_plan.md format looks valid ({rp_result.get('size', 0)} bytes)")
            print(f"       Tasks: {todo} TODO, {in_prog} in-progress, {done} done")

    # --- Summary ---
    print()
    print("=" * 50)
    critical_count = sum(1 for i in all_issues if i.startswith("CRITICAL"))
    warning_count = sum(1 for i in all_issues if i.startswith("WARNING"))
    suspect_count = sum(1 for i in all_issues if i.startswith("SUSPECT"))

    if has_critical_failure:
        print(f"RESULT: FAIL ({critical_count} critical, {warning_count} warnings)")
        print("Action: Fix critical issues before proceeding to Mode B.")
        sys.exit(1)
    elif warning_count > 0 or suspect_count > 0:
        print(f"RESULT: WARN ({warning_count} warnings, {suspect_count} suspects)")
        print("Action: Can proceed to Mode B with noted limitations.")
        sys.exit(2)
    else:
        print("RESULT: ALL PASS")
        print("Action: Ready to proceed to Mode B (Renderer).")
        sys.exit(0)


if __name__ == "__main__":
    main()
