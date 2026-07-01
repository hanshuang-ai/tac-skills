#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Validate tac-ux-mastergo handoff documents.

Python 3.6+ required.
"""

import argparse
import io
import json
import os
import re
import sys


REQUIRED_SECTIONS = [
    u"输入与依据",
    u"页面语义卡",
    u"下游稳定契约",
    u"交互对象清单",
    u"业务规则清单",
    u"状态模型",
    u"事件/意图/副作用模型",
    u"状态转移表",
    u"边界态矩阵",
    u"导航与宿主协作",
    u"数据规则与接口期望",
    u"全局/跨页规则",
    u"与视觉稿协作说明",
    u"实现落点建议",
    u"代码冲突检查",
    u"待确认项",
    u"验收清单",
]

REQUIRED_TERMS = [
    u"business-source",
    u"interaction-source",
    u"visual-source",
    u"code-reference",
    u"implemented/missing/wrong/conflicting/reusable/pending",
    u"interaction-fact/visual-evidence/implementation-suggestion",
    u"page-local/cross-page-shared/host-owned/global/ownership-conflict",
]

UI_MAPPING_TERMS = [
    u"primary-carrier/secondary-carrier/state-container/event-trigger/feedback-surface",
    u"page/section/component/overlay",
    u"required/provisional/optional",
]

BOUNDARY_TERMS = [
    u"loading",
    u"empty",
    u"error",
    u"offline",
    u"disabled",
    u"permission-denied",
    u"retry",
]

TABLE_REQUIREMENTS = [
    (
        u"输入与依据",
        [u"来源类型", u"输入物", u"位置/节点/章节", u"用途", u"可信度"],
    ),
    (
        u"下游稳定契约",
        [u"契约对象", u"稳定名称", u"说明", u"变更规则"],
    ),
    (
        u"业务规则清单",
        [
            u"规则 ID",
            u"规则描述",
            u"证据层",
            u"归属",
            u"来源类型",
            u"来源位置",
            u"置信度",
            u"待确认",
        ],
    ),
    (
        u"状态转移表",
        [u"当前状态", u"事件/意图", u"Guard 条件", u"下一状态", u"副作用", u"来源规则"],
    ),
    (
        u"边界态矩阵",
        [u"场景", u"进入条件", u"页面表现", u"可操作项", u"恢复/退出规则", u"来源"],
    ),
    (
        u"待确认项",
        [
            u"编号",
            u"问题",
            u"确认角色",
            u"跑偏风险",
            u"阻塞级别",
            u"推荐选项",
            u"可继续假设",
            u"建议确认时机",
            u"影响范围",
        ],
    ),
]

UI_COORDINATION_COLUMNS = [
    u"交互对象 ID",
    u"UI 角色",
    u"映射关系",
    u"承载级别",
    u"所属页面/区域",
    u"是否关键",
    u"缺失时的临时承接策略",
]

# Global handoff §12 can use a reduced column set (no visual-design-specific columns)
GLOBAL_UI_COORDINATION_COLUMNS = [
    u"交互对象 ID",
    u"UI 角色",
    u"映射关系",
    u"承载级别",
    u"是否关键",
]

EVIDENCE_VALUES = [
    u"interaction-fact",
    u"visual-evidence",
    u"implementation-suggestion",
]

OWNERSHIP_VALUES = [
    u"page-local",
    u"cross-page-shared",
    u"host-owned",
    u"global",
    u"ownership-conflict",
]

SOURCE_TYPE_VALUES = [
    u"business-source",
    u"interaction-source",
    u"visual-source",
    u"architecture-source",
    u"code-reference",
]

CONFIDENCE_VALUES = [
    u"confirmed",
    u"pending",
    u"candidate",
    u"assumption",
]

BLOCKING_VALUES = [
    u"pre-blocking",
    u"blocking",
    u"non-blocking",
]

# ---- Mermaid validation constants ----
MERMAID_TRANSITION_RE = re.compile(
    r"^\s*(\S+)\s*-->\s*(\S+)\s*(?::\s*(.+))?\s*$"
)

# Flowchart scene detection thresholds
FLOWCHART_DECISION_MIN = 2       # minimum "?" decision nodes
FLOWCHART_BRANCH_PAIR_MIN = 2    # minimum paired "是"/"否" branches

# Component names that are likely placeholders, not actual UX copy
INSTANCE_PLACEHOLDER_NAMES = {
    u"提示文本", u"按钮", u"图标", u"标签",
    u"placeholder", u"hint", u"label",
}

CONFIRMATION_OWNER_VALUES = [
    u"product",
    u"interaction",
    u"visual",
    u"technical",
    u"host",
    u"data",
    u"mixed",
]

DRIFT_RISK_VALUES = [
    u"state",
    u"data",
    u"navigation",
    u"effect",
    u"ownership",
    u"ui-carrier",
    u"acceptance",
    u"none",
]

GLOBAL_SCOPE_MARKERS = [
    u"global",
    u"shared",
    u"cross-page",
    u"全局",
    u"共享",
    u"跨页",
]


def read_text(path):
    with io.open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def normalize_heading(line):
    match = re.match(r"^\s*(#{1,6})\s+(.*?)(?:\s+#*)?\s*$", line)
    if not match:
        return None
    level = len(match.group(1))
    title = match.group(2).strip()
    title = re.sub(r"^\d+(?:\.\d+)*[.)、]?\s*", "", title)
    return (level, title)


def collect_headings(text):
    headings = []
    for line in text.splitlines():
        heading = normalize_heading(line)
        if heading:
            headings.append(heading)
    return headings


def has_section(headings, section):
    for _, heading in headings:
        if section in heading:
            return True
    return False


def split_table_row(line):
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    cells = stripped.strip("|").split("|")
    return [cell.strip().strip("`").strip() for cell in cells]


def is_separator_row(cells):
    if not cells:
        return False
    for cell in cells:
        if not re.match(r"^\s*:?-{2,}:?\s*$", cell):
            return False
    return True


def collect_tables(text):
    tables = []
    current = []

    for line in text.splitlines():
        cells = split_table_row(line)
        if cells is None:
            if current:
                tables.append(current)
                current = []
            continue
        current.append(cells)

    if current:
        tables.append(current)

    normalized = []
    for table in tables:
        if len(table) < 2:
            continue
        header = table[0]
        data_start = 1
        if is_separator_row(table[1]):
            data_start = 2
        normalized.append({"header": header, "rows": table[data_start:]})

    return normalized


def section_text(text, section):
    """Return body text under a ## section, treating deeper headings (# sub>) as
    internal content rather than section boundaries."""
    pattern = re.compile(r"^\s*(#{1,6})\s+(.*?)(?:\s+#*)?\s*$", re.MULTILINE)
    matches = list(pattern.finditer(text))

    target_level = None
    target_index = None

    for index, match in enumerate(matches):
        level = len(match.group(1))
        raw_title = match.group(2).strip()
        title = re.sub(r"^\d+(?:\.\d+)*[.)、]?\s*", "", raw_title)
        if section in title:
            target_level = level
            target_index = index
            break

    if target_index is None:
        return u""

    start = matches[target_index].end()
    end = len(text)

    # Only headings at the same level or higher serve as section boundaries;
    # deeper sub-headings (###, ####, …) remain part of this section's body.
    for next_index in range(target_index + 1, len(matches)):
        next_level = len(matches[next_index].group(1))
        if next_level <= target_level:
            end = matches[next_index].start()
            break

    return text[start:end]


def find_table(text, section, required_headers):
    body = section_text(text, section)
    for table in collect_tables(body):
        if has_headers(table["header"], required_headers):
            return table
    return None


def has_headers(header, required_headers):
    for required in required_headers:
        if required not in header:
            return False
    return True


def row_dict(header, row):
    result = {}
    for index, key in enumerate(header):
        if index < len(row):
            result[key] = row[index].strip()
        else:
            result[key] = u""
    return result


def normalized_value(value):
    return value.strip().lower()


def contains_any(value, allowed):
    normalized = normalized_value(value)
    for item in allowed:
        if item.lower() in normalized:
            return True
    return False


def concrete_row(row):
    non_empty = [cell for cell in row if cell.strip()]
    if not non_empty:
        return False

    joined = u" ".join(non_empty)
    slash_count = joined.count("/")
    option_hits = 0
    for values in (
        EVIDENCE_VALUES,
        OWNERSHIP_VALUES,
        SOURCE_TYPE_VALUES,
        CONFIDENCE_VALUES,
        BLOCKING_VALUES,
    ):
        for value in values:
            if value in joined:
                option_hits += 1

    if slash_count > 0 and option_hits > 2:
        return False

    return True


def validate_table_headers(text, errors):
    is_global = handoff_looks_global_or_shared(text)

    for section, required_headers in TABLE_REQUIREMENTS:
        body = section_text(text, section)
        if not body:
            continue
        table = find_table(text, section, required_headers)
        if table is None:
            errors.append(
                u"Section table missing required columns: {0} ({1})".format(
                    section, u", ".join(required_headers)
                )
            )

    # §12: visual coordination
    if section_text(text, u"与视觉稿协作说明"):
        columns_to_check = GLOBAL_UI_COORDINATION_COLUMNS if is_global else UI_COORDINATION_COLUMNS
        if find_table(text, u"与视觉稿协作说明", columns_to_check) is None:
            errors.append(
                u"UI coordination section missing required table columns: {0}".format(
                    u", ".join(columns_to_check)
                )
            )


def validate_business_rules(text, errors, warnings):
    table = find_table(
        text,
        u"业务规则清单",
        [
            u"规则 ID",
            u"规则描述",
            u"证据层",
            u"归属",
            u"来源类型",
            u"来源位置",
            u"置信度",
        ],
    )
    if table is None:
        return

    concrete_count = 0
    for row_number, row in enumerate(table["rows"], 1):
        if not concrete_row(row):
            continue

        item = row_dict(table["header"], row)
        rule_id = item.get(u"规则 ID", u"")
        rule_desc = item.get(u"规则描述", u"")
        if not rule_id and not rule_desc:
            continue

        concrete_count += 1
        row_label = rule_id or u"row {0}".format(row_number)
        evidence = item.get(u"证据层", u"")
        ownership = item.get(u"归属", u"")
        source_type = item.get(u"来源类型", u"")
        source_location = item.get(u"来源位置", u"")
        confidence = item.get(u"置信度", u"")

        if not contains_any(evidence, EVIDENCE_VALUES):
            errors.append(u"Business rule {0} has invalid evidence layer.".format(row_label))

        if not contains_any(ownership, OWNERSHIP_VALUES):
            errors.append(u"Business rule {0} has invalid ownership.".format(row_label))

        if not contains_any(confidence, CONFIDENCE_VALUES):
            errors.append(u"Business rule {0} has invalid confidence.".format(row_label))

        if source_type and not contains_any(source_type, SOURCE_TYPE_VALUES):
            errors.append(u"Business rule {0} has invalid source type.".format(row_label))

        if contains_any(confidence, [u"confirmed"]):
            if not source_type or not source_location:
                errors.append(
                    u"Confirmed business rule {0} must include source type and source location.".format(
                        row_label
                    )
                )
            if contains_any(source_type, [u"code-reference"]):
                errors.append(
                    u"Confirmed business rule {0} must not use code-reference as business evidence.".format(
                        row_label
                    )
                )

        if contains_any(evidence, [u"visual-evidence"]) and contains_any(confidence, [u"confirmed"]):
            if not contains_any(source_type, [u"business-source", u"interaction-source"]):
                warnings.append(
                    u"Business rule {0} is confirmed from visual evidence without business/interaction source.".format(
                        row_label
                    )
                )

        if contains_any(evidence, [u"implementation-suggestion"]) and contains_any(
            confidence, [u"confirmed"]
        ):
            warnings.append(
                u"Business rule {0} is confirmed but marked as implementation-suggestion.".format(
                    row_label
                )
            )

    if concrete_count == 0:
        warnings.append(u"Business rule table has no concrete rule rows.")


def validate_rule_granularity(text, errors):
    """SEMANTIC: Check that each business rule contains at most one independent action.

    Each rule MUST represent a single trigger-condition-result triplet.
    Compound rules (multiple → arrows or multiple distinct action verbs)
    are detected and reported as errors.
    """
    table = find_table(
        text,
        u"业务规则清单",
        [u"规则 ID", u"规则描述"],
    )
    if table is None:
        return

    ACTION_VERBS = [
        u"点击", u"切换", u"滑动", u"长按", u"确认", u"取消", u"关闭",
        u"显示", u"隐藏", u"跳转", u"弹出", u"返回", u"输入",
        u"click", u"toggle", u"swipe", u"long-press", u"long_press",
        u"confirm", u"cancel", u"close", u"show", u"hide",
        u"navigate", u"popup", u"back", u"input",
    ]

    for row_number, row in enumerate(table["rows"], 1):
        if not concrete_row(row):
            continue
        item = row_dict(table["header"], row)
        rule_id = item.get(u"规则 ID", u"") or u"row {0}".format(row_number)
        rule_desc = item.get(u"规则描述", u"")

        if not rule_desc:
            continue

        # Count → arrows (each arrow indicates an action-result chain)
        arrow_count = rule_desc.count(u"\u2192")  # →
        if arrow_count >= 2:
            errors.append(
                u"SEMANTIC: Business rule {0} contains {1} independent action chains "
                u"(→ arrows). Split into {1} separate trigger-condition-result rules.".format(
                    rule_id, arrow_count
                )
            )
            continue

        # Count distinct action verbs within the description
        desc_lower = rule_desc.lower()
        verb_hits = 0
        for verb in ACTION_VERBS:
            if verb in desc_lower:
                verb_hits += 1

        if verb_hits >= 2:
            errors.append(
                u"SEMANTIC: Business rule {0} may contain {1} distinct actions "
                u"({2} verb keywords matched). Each rule MUST represent a single "
                u"trigger-condition-result triplet. Split compound rules.".format(
                    rule_id, verb_hits, verb_hits
                )
            )


def validate_sub_component_coverage(text, warnings):
    """SEMANTIC: Check that §3 interaction objects have corresponding sub-state groups in §5.

    For each interaction object with ≥2 distinct visible configurations, a sub-state
    group should exist in §5 or be explicitly marked 'no independent state'.
    """
    interaction_table = find_table(
        text,
        u"交互对象清单",
        [u"交互对象 ID"],
    )
    if interaction_table is None:
        return

    object_count = 0
    for row in interaction_table["rows"]:
        if not concrete_row(row):
            continue
        item = row_dict(interaction_table["header"], row)
        if item.get(u"交互对象 ID", u"").strip():
            object_count += 1

    if object_count < 2:
        return  # Only 0–1 objects; ratio check is not meaningful

    # Count §5 sub-state groups: tables with ≥1 concrete data row within §5
    section5_body = section_text(text, u"状态模型")
    if not section5_body:
        return

    tables_in_s5 = collect_tables(section5_body)
    sub_state_count = 0
    for table in tables_in_s5:
        # Skip the primary state model header-only table
        has_data = any(concrete_row(row) for row in table["rows"])
        if has_data:
            sub_state_count += 1

    # Also scan for "no independent state" markers in §5
    no_independent_count = 0
    if u"no independent state" in section5_body.lower():
        # Count occurrences — one per object that is explicitly marked
        no_independent_count = section5_body.lower().count(u"no independent state")

    effective_objects = max(object_count - no_independent_count, 1)
    ratio = float(sub_state_count) / float(effective_objects)

    if ratio < 0.5:
        warnings.append(
            u"SEMANTIC: §3 has {0} interaction object(s) but §5 has only {1} sub-state "
            u"group(s) (coverage ratio {2:.0%} after excluding {3} 'no independent state' "
            u"marker(s)). Add sub-state groups for objects with ≥2 distinct visible "
            u"configurations, or explicitly mark 'no independent state' where omission "
            u"is intentional.".format(
                object_count, sub_state_count, ratio, no_independent_count
            )
        )


def validate_change_record(text, errors, warnings):
    """SEMANTIC: Check that §0.2 交互更新记录 has at least one concrete change row.

    The change record (§0.2) is the centralized audit trail for all confirmation
    decisions and maintenance actions. An empty change record means confirmation
    triage results have not been written back.
    """
    body = section_text(text, u"交互更新记录")
    if not body:
        body = section_text(text, u"变更记录")
    if not body:
        body = section_text(text, u"0.2")
        if not body:
            warnings.append(
                u"SEMANTIC: §0.2 交互更新记录 section is missing. "
                u"Add a change record table to track confirmation decisions and "
                u"maintenance history."
            )
            return

    tables = collect_tables(body)
    if not tables:
        warnings.append(
            u"SEMANTIC: §0.2 交互更新记录 section has no table. "
            u"Add a table with columns: Change ID, Type, Source, Description, "
            u"Affected sections."
        )
        return

    # Check if any table has ≥1 concrete row
    has_concrete = False
    for table in tables:
        for row in table["rows"]:
            if not concrete_row(row):
                continue
            item = row_dict(table["header"], row)
            # Probe for an identifier in the first recognizable column
            change_id = (
                item.get(u"Change ID", u"").strip()
                or item.get(u"Version/Date", u"").strip()
                or item.get(u"Version", u"").strip()
                or item.get(u"Date", u"").strip()
            )
            if change_id and change_id.strip(u"- :\u2500"):
                has_concrete = True
                break
        if has_concrete:
            break

    if not has_concrete:
        # Check whether §15 has confirmed/resolved items that SHOULD have been written back
        pending_body = section_text(text, u"待确认项")
        has_confirmed_pending = bool(
            pending_body
            and (
                u"~~" in pending_body
                or u"resolved" in pending_body.lower()
                or u"\u2713" in pending_body  # ✓
            )
        )

        if has_confirmed_pending:
            errors.append(
                u"SEMANTIC: §0.2 交互更新记录 has no concrete change rows, "
                u"but §15 待确认项 contains resolved/confirmed items. "
                u"Write every confirmation decision back to §0.2 as an audit-trail row "
                u"(Change ID, Type, Description, Affected sections)."
            )
        else:
            warnings.append(
                u"SEMANTIC: §0.2 交互更新记录 has no concrete change rows. "
                u"Record at minimum the initial creation or latest maintenance reason, "
                u"date, and scope."
            )



def validate_state_transitions(text, warnings):
    table = find_table(
        text,
        u"状态转移表",
        [u"当前状态", u"事件/意图", u"下一状态", u"来源规则"],
    )
    if table is None:
        return

    concrete_count = 0
    for row_number, row in enumerate(table["rows"], 1):
        if not concrete_row(row):
            continue
        item = row_dict(table["header"], row)
        if not item.get(u"当前状态") and not item.get(u"事件/意图") and not item.get(u"下一状态"):
            continue

        concrete_count += 1
        missing = []
        for column in [u"当前状态", u"事件/意图", u"下一状态", u"来源规则"]:
            if not item.get(column, u"").strip():
                missing.append(column)
        if missing:
            warnings.append(
                u"State transition row {0} missing recommended fields: {1}".format(
                    row_number, u", ".join(missing)
                )
            )

    if concrete_count == 0:
        warnings.append(u"State transition table has no concrete transition rows.")


def validate_pending_items(text, errors):
    table = find_table(
        text,
        u"待确认项",
        [u"编号", u"问题", u"确认角色", u"跑偏风险", u"阻塞级别", u"影响范围"],
    )
    if table is None:
        return

    for row_number, row in enumerate(table["rows"], 1):
        if not concrete_row(row):
            continue
        item = row_dict(table["header"], row)
        if not item.get(u"编号") and not item.get(u"问题"):
            continue

        level = item.get(u"阻塞级别", u"")
        if not contains_any(level, BLOCKING_VALUES):
            errors.append(
                u"Pending item row {0} has invalid blocking level.".format(row_number)
            )

        owner = item.get(u"确认角色", u"")
        if not contains_any(owner, CONFIRMATION_OWNER_VALUES):
            errors.append(
                u"Pending item row {0} has invalid confirmation owner.".format(row_number)
            )

        drift_risk = item.get(u"跑偏风险", u"")
        if not contains_any(drift_risk, DRIFT_RISK_VALUES):
            errors.append(
                u"Pending item row {0} has invalid implementation drift risk.".format(
                    row_number
                )
            )


def handoff_looks_global_or_shared(text):
    probe_sections = [
        u"产物定位与落盘",
        u"页面语义卡",
        u"规则协议语义",
        u"全局/跨页规则",
    ]
    probe = u""
    lines = text.splitlines()
    if lines:
        probe += lines[0] + u"\n"
    for section in probe_sections:
        probe += section_text(text, section) + u"\n"

    return contains_any(probe, GLOBAL_SCOPE_MARKERS)


def pending_mentions_ownership(text):
    body = section_text(text, u"待确认项")
    return u"ownership-conflict" in body or u"归属" in body or u"ownership" in body.lower()


def validate_feedback_copy(text, warnings, dsl_text_node_count=None):
    """Check that the feedback copy inventory (§6.3) is present and covers expected types.

    When dsl_text_node_count is provided (e.g. from cached trimmed DSL), the
    function also cross-validates feedback-copy coverage against DSL visible text.
    """
    table = find_table(
        text,
        u"反馈文案清单",
        [u"文案", u"反馈类型", u"触发事件"],
    )
    if table is None:
        warnings.append(
            u"Feedback copy inventory (§6.3) table is missing or incomplete. "
            u"Ensure toast messages, prompt text, empty-state copy, error/success "
            u"messages, and button-state labels are extracted."
        )
        return

    concrete_count = 0
    feedback_types_found = set()
    for row in table["rows"]:
        if not concrete_row(row):
            continue
        item = row_dict(table["header"], row)
        copy_text = item.get(u"文案", u"").strip()
        if not copy_text:
            continue
        concrete_count += 1
        feedback_types_found.add(item.get(u"反馈类型", u"").strip().lower())

    if concrete_count < 3:
        warnings.append(
            u"Feedback copy inventory has only {0} item(s). "
            u"Re-scan DSL for all visible toast, prompt, error, success, "
            u"empty-state, and button-label text.".format(concrete_count)
        )

    expected_type_groups = [
        {u"toast", u"toast"},
        {u"prompt", u"bubble", u"hint", u"text"},
        {u"empty", u"empty-state"},
        {u"error", u"fail", u"failure"},
        {u"success"},
        {u"button", u"button-label", u"label", u"btn"},
    ]
    missing_types = []
    for group in expected_type_groups:
        if not group.intersection(feedback_types_found):
            most_representative = next(iter(group))
            missing_types.append(most_representative)

    if missing_types:
        warnings.append(
            u"Feedback copy inventory may be incomplete — potentially missing "
            u"these feedback type categories: {0}. "
            u"Ensure toast messages, button state labels, empty-state prompts, "
            u"and inline error/success text are extracted.".format(
                u", ".join(missing_types)
            )
        )

    # ---- DSL visible-text cross-check (SEMANTIC) ----
    if dsl_text_node_count is not None and dsl_text_node_count > 0:
        if concrete_count > 0:
            coverage_pct = float(concrete_count) / float(dsl_text_node_count)
            if coverage_pct < 0.5:
                warnings.append(
                    u"SEMANTIC: Feedback copy inventory covers only {0:.0%} of DSL "
                    u"visible text nodes ({1} feedback entries vs {2} DSL text nodes). "
                    u"Re-scan DSL for missed toast, button labels, empty-state copy, "
                    u"and inline error/success messages.".format(
                        coverage_pct, concrete_count, dsl_text_node_count
                    )
                )


def validate_page_global_ownership(text, warnings):
    is_global_or_shared = handoff_looks_global_or_shared(text)

    # Check both "页面语义卡" (page handoff) and "规则协议语义" (global handoff)
    semantic_table = find_table(text, u"页面语义卡", [u"字段", u"结论", u"来源", u"待确认"])
    if semantic_table is None:
        semantic_table = find_table(text, u"规则协议语义", [u"字段", u"结论", u"来源", u"待确认"])
    if semantic_table is not None:
        for row in semantic_table["rows"]:
            item = row_dict(semantic_table["header"], row)
            field = item.get(u"字段", u"")
            if field == u"页面级细节归属" and not item.get(u"结论", u"").strip():
                warnings.append(
                    u"Page-level detail ownership is empty; clarify what stays page-local."
                )

    business_table = find_table(
        text,
        u"业务规则清单",
        [u"规则 ID", u"规则描述", u"归属", u"置信度"],
    )
    if business_table is not None:
        has_ownership_conflict = False
        for row_number, row in enumerate(business_table["rows"], 1):
            if not concrete_row(row):
                continue
            item = row_dict(business_table["header"], row)
            rule_id = item.get(u"规则 ID", u"") or u"row {0}".format(row_number)
            ownership = item.get(u"归属", u"")
            confidence = item.get(u"置信度", u"")

            if contains_any(ownership, [u"ownership-conflict"]):
                has_ownership_conflict = True

            if is_global_or_shared and contains_any(ownership, [u"page-local"]):
                warnings.append(
                    u"Global/shared handoff contains page-local business rule {0}; reference the page owner or mark ownership-conflict if unresolved.".format(
                        rule_id
                    )
                )

            if contains_any(ownership, [u"ownership-conflict"]) and contains_any(
                confidence, [u"confirmed"]
            ):
                warnings.append(
                    u"Business rule {0} is confirmed but ownership is still conflicting.".format(
                        rule_id
                    )
                )

        if has_ownership_conflict and not pending_mentions_ownership(text):
            warnings.append(
                u"Ownership conflict exists but no matching pending item was found."
            )

    # Try page-handoff "全局/跨页规则" table and global-handoff "消费页面证据矩阵" table
    global_table = find_table(
        text,
        u"全局/跨页规则",
        [u"规则", u"影响范围", u"归属建议", u"状态"],
    )
    if global_table is None and is_global_or_shared:
        global_table = find_table(
            text,
            u"消费页面证据矩阵",
            [u"消费页面", u"消费方式", u"来源"],
        )
    if global_table is not None:
        for row_number, row in enumerate(global_table["rows"], 1):
            if not concrete_row(row):
                continue
            item = row_dict(global_table["header"], row)
            if not item.get(u"规则", u"").strip():
                continue
            # Select column set based on table type
            is_consumer_table = u"消费页面" in global_table["header"]
            required_columns = (
                [u"消费页面", u"消费方式", u"来源"]
                if is_consumer_table
                else [
                    u"影响范围",
                    u"当前页消费方式",
                    u"归属建议",
                    u"状态",
                    u"来源",
                ]
            )
            missing = []
            for column in required_columns:
                if not item.get(column, u"").strip():
                    missing.append(column)
            if missing:
                warnings.append(
                    u"Global/cross-page rule row {0} missing ownership governance fields: {1}".format(
                        row_number, u", ".join(missing)
                    )
                )


# ============================================================
#  NEW: Mermaid + DSL-aware checks (2026-05-26)
# ============================================================

def _flatten_nodes(nodes, result):
    """Recursively flatten DSL node tree into a flat list."""
    if not nodes:
        return
    for node in nodes:
        result.append(node)
        children = node.get("children", [])
        if children:
            _flatten_nodes(children, result)


def _extract_all_text(node):
    """Extract all visible text from a DSL node (name + text array)."""
    parts = []
    name = node.get("name", "") or ""
    if name:
        parts.append(name)
    text_items = node.get("text", [])
    for item in text_items:
        if isinstance(item, dict):
            t = item.get("text", "")
            if t:
                parts.append(t)
        elif isinstance(item, str):
            parts.append(item)
    return u" ".join(parts)


def _count_flowchart_patterns(dsl):
    """Return (decision_count, branch_pair_count) from trimmed DSL."""
    if not dsl:
        return 0, 0

    try:
        nodes = dsl.get("dsl", {}).get("nodes", [])
    except (AttributeError, KeyError):
        return 0, 0

    all_nodes = []
    _flatten_nodes(nodes, all_nodes)

    decision_count = 0
    for node in all_nodes:
        combined = _extract_all_text(node)
        if u"?" in combined:
            decision_count += 1

    yes_labels = {u"是"}
    no_labels = {u"否"}
    yes_count = 0
    no_count = 0
    for node in all_nodes:
        text_content = _extract_all_text(node).strip()
        if text_content in yes_labels:
            yes_count += 1
        if text_content in no_labels:
            no_count += 1

    branch_pair_count = min(yes_count, no_count)
    return decision_count, branch_pair_count


def _extract_mermaid_blocks(text):
    """Return list of content strings from ```mermaid ... ``` blocks."""
    blocks = []
    pattern = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)
    for match in pattern.finditer(text):
        blocks.append(match.group(1))
    return blocks


def _parse_mermaid_transitions(block):
    """Parse STATE --> STATE [: label] lines from a mermaid block.

    Returns (transitions, unparseable_lines) where transitions is
    a list of (src, dst, label) tuples.
    """
    transitions = []
    unparseable = []

    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("%%") or line.startswith("--"):
            continue
        match = MERMAID_TRANSITION_RE.match(line)
        if match:
            src = match.group(1).strip()
            dst = match.group(2).strip()
            label = (match.group(3) or "").strip()
            transitions.append((src, dst, label))
        else:
            # Only count lines that look like they SHOULD be transitions
            if "-->" in line or "->" in line:
                unparseable.append(line)

    return transitions, unparseable


def _extract_defined_states(block):
    """Extract state names defined in a mermaid stateDiagram block.

    Handles:
      state "Label" as STATE  -> extracts STATE
      STATE : description     -> extracts STATE
    Also handles simple state names on their own lines.
    """
    defined = set()
    # state "Label" as STATE
    for match in re.finditer(r'state\s+"[^"]*"\s+as\s+(\S+)', block):
        defined.add(match.group(1))
    # STATE : description
    for line in block.splitlines():
        stripped = line.strip()
        if ":" in stripped:
            name = stripped.split(":")[0].strip()
            if name and not name.startswith("state") and " " not in name:
                defined.add(name)
    return defined


def validate_mermaid_syntax(text, errors):
    """T1+T2: Parse transitions and check node-set consistency (ERROR)."""
    blocks = _extract_mermaid_blocks(text)
    if not blocks:
        return

    for idx, block in enumerate(blocks):
        block_label = u"block {0}".format(idx + 1) if len(blocks) > 1 else u"block"

        transitions, unparseable = _parse_mermaid_transitions(block)

        # T1: Syntax
        if unparseable:
            errors.append(
                u"Mermaid {0}: {1} transition line(s) failed to parse "
                u"(expected format: 'STATE --> STATE[: label]'). "
                u"Problem lines: {2}".format(
                    block_label, len(unparseable),
                    u"; ".join(unparseable[:3])
                )
            )

        if not transitions:
            errors.append(
                u"Mermaid {0}: No parseable transitions found. "
                u"Add 'STATE --> STATE' transition lines.".format(block_label)
            )
            continue

        # T2: Node-set consistency
        defined = _extract_defined_states(block)
        referenced = set()
        for src, dst, _ in transitions:
            referenced.add(src)
            referenced.add(dst)

        # [*] is a Mermaid built-in, exclude from checks
        undefined = referenced - defined - {u"[*]"}
        if undefined:
            errors.append(
                u"Mermaid {0}: References undefined state(s): {1}. "
                u"Either define these states in the diagram or fix the "
                u"transition references.".format(
                    block_label, u", ".join(sorted(undefined))
                )
            )


def _build_graph_degrees(transitions):
    """Return (in_degree, out_degree) dicts from transition list."""
    in_deg = {}
    out_deg = {}
    for src, dst, _ in transitions:
        out_deg[src] = out_deg.get(src, 0) + 1
        in_deg[dst] = in_deg.get(dst, 0) + 1
    return in_deg, out_deg


def validate_mermaid_reachability(text, warnings):
    """T3: Check dead-end and orphan states in Mermaid diagrams (WARN)."""
    blocks = _extract_mermaid_blocks(text)
    if not blocks:
        return

    for idx, block in enumerate(blocks):
        transitions, _ = _parse_mermaid_transitions(block)
        if len(transitions) < 2:
            continue

        in_deg, out_deg = _build_graph_degrees(transitions)

        all_states = set()
        for src, dst, _ in transitions:
            if src != u"[*]":
                all_states.add(src)
            if dst != u"[*]":
                all_states.add(dst)

        dead_ends = {s for s in all_states if out_deg.get(s, 0) == 0}
        orphans = {s for s in all_states if in_deg.get(s, 0) == 0}

        block_label = u"block {0}".format(idx + 1) if len(blocks) > 1 else u"block"

        if dead_ends:
            warnings.append(
                u"Mermaid {0}: State(s) have no outgoing transitions (dead end): "
                u"{1}. This may be intentional (terminal state) or a missing "
                u"recovery path. Review manually.".format(
                    block_label, u", ".join(sorted(dead_ends))
                )
            )

        if orphans:
            warnings.append(
                u"Mermaid {0}: State(s) have no incoming transitions (orphan): "
                u"{1}. This may be intentional (initial state reached via [*]) "
                u"or a missing entry path. Review manually.".format(
                    block_label, u", ".join(sorted(orphans))
                )
            )


def _load_dsl(path):
    """Load trimmed DSL JSON from a file path. Returns None on failure."""
    if not path or not os.path.isfile(path):
        return None
    try:
        with io.open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (ValueError, IOError):
        return None


def _mermaid_heuristic_check(text, warnings):
    """Weak inference when --dsl is not available: scan §7 transition table
    and recovery keywords to guess whether a Mermaid diagram is warranted.
    """
    table = find_table(
        text,
        u"状态转移表",
        [u"当前状态", u"事件/意图", u"下一状态", u"来源规则"],
    )

    state_variants = 0
    if table:
        states = set()
        for row in table["rows"]:
            item = row_dict(table["header"], row)
            src = item.get(u"当前状态", u"").strip()
            dst = item.get(u"下一状态", u"").strip()
            if src:
                states.add(src)
            if dst:
                states.add(dst)
        state_variants = len(states)

    # Search for recovery/branch/flow keywords in business rules (§4)
    recovery_keywords = [u"恢复", u"重试", u"断点", u"流程", u"重连", u"自动续传"]
    body = section_text(text, u"业务规则清单") or u""
    keyword_hits = [kw for kw in recovery_keywords if kw in body]

    if state_variants >= 3 and keyword_hits:
        warnings.append(
            u"SEMANTIC: Handoff state model has {0} state variants and "
            u"recovery/branch keywords ({1}) "
            u"but no ```mermaid diagram. "
            u"Consider adding a Mermaid stateDiagram for topological "
            u"verification (dead-end states, orphan states, unreachable "
            u"transitions). "
            u"Provide --dsl <path> for automatic flowchart detection."
            .format(state_variants, u", ".join(sorted(set(keyword_hits))[:3]))
        )


def validate_mermaid_should_exist(text, dsl_path, warnings):
    """WARN when DSL contains flowchart evidence but handoff lacks Mermaid."""
    if "```mermaid" in text:
        return  # Already has Mermaid

    if not dsl_path:
        # ── Heuristic fallback: scan handoff text for state complexity ──
        _mermaid_heuristic_check(text, warnings)
        warnings.append(
            u"SEMANTIC: Cannot verify whether Mermaid diagram is needed — "
            u"no DSL cache path provided. "
            u"Provide --dsl <path> to enable automatic flowchart detection."
        )
        return

    dsl = _load_dsl(dsl_path)
    if not dsl:
        warnings.append(
            u"SEMANTIC: Cannot verify whether Mermaid diagram is needed — "
            u"DSL cache file missing or invalid: {0}. "
            u"Run cache_dsl.py to generate trimmed DSL, then re-validate."
            .format(dsl_path)
        )
        return

    decision_count, branch_pair_count = _count_flowchart_patterns(dsl)

    if decision_count >= FLOWCHART_DECISION_MIN and branch_pair_count >= FLOWCHART_BRANCH_PAIR_MIN:
        warnings.append(
            u"SEMANTIC: DSL contains flowchart evidence "
            u"({0} decision nodes, {1} paired branches) "
            u"but handoff has no ```mermaid diagram. "
            u"Restore the flowchart as a Mermaid stateDiagram. "
            u"NOTE: Mermaid correctness is NOT validated - review manually."
            .format(decision_count, branch_pair_count)
        )


def _detect_unresolved_components(dsl):
    """Detect INSTANCE nodes whose text may not be fully resolved.

    Returns list of (node_id, parent_frame_name, component_id, name).
    """
    unresolved = []
    if not dsl:
        return unresolved

    try:
        nodes = dsl.get("dsl", {}).get("nodes", [])
    except (AttributeError, KeyError):
        return unresolved

    all_nodes = []
    _flatten_nodes(nodes, all_nodes)

    # Build a node-id-based parent map
    id_parent_map = {}
    def _build_id_parent_map(node_list, parent_name=None):
        for node in node_list:
            name = node.get("name", "") or u""
            nid = node.get("id", "")
            id_parent_map[nid] = parent_name or name
            children = node.get("children", [])
            if children:
                _build_id_parent_map(children, name)

    _build_id_parent_map(nodes)

    for node in all_nodes:
        if node.get("type") != "INSTANCE":
            continue

        component_id = node.get("componentId", "")
        if not component_id:
            continue

        name = (node.get("name", "") or "").strip()
        node_id = node.get("id", "")

        # Check if the name looks like a placeholder
        is_placeholder = (
            not name
            or name.lower() in {n.lower() for n in INSTANCE_PLACEHOLDER_NAMES}
        )

        if is_placeholder:
            parent = id_parent_map.get(node_id, u"unknown")
            unresolved.append((node_id, parent, component_id, name))

    return unresolved


def validate_instance_components(text, dsl_path, warnings):
    """E4: WARN about INSTANCE components whose text is not fully resolved."""
    if not dsl_path:
        return

    dsl = _load_dsl(dsl_path)
    if not dsl:
        return

    unresolved = _detect_unresolved_components(dsl)
    if not unresolved:
        return

    items = []
    for node_id, parent, comp_id, name in unresolved[:5]:  # cap at 5
        items.append(u"{0} (in '{1}', componentId={2})".format(
            node_id, parent, comp_id
        ))

    warnings.append(
        u"SEMANTIC: DSL contains {0} INSTANCE component(s) whose visible text "
        u"may not be fully resolved in trimmed DSL: {1}. "
        u"Verify the actual feedback copy text inside these components and "
        u"add to {2}6.3 Feedback Copy Inventory if missing."
        .format(
            len(unresolved),
            u"; ".join(items),
            u"\u00a7"  # §
        )
    )


def validate_dsl_aware_checks(text, dsl_path, warnings):
    """Run all checks that depend on trimmed DSL data."""
    validate_mermaid_should_exist(text, dsl_path, warnings)
    validate_instance_components(text, dsl_path, warnings)


def _looks_like_index(text, path):
    """Detect UX handoff index files by structure markers.

    Index files have a distinct structure (交互稿清单与进度 navigation table,
    待确认项汇总, etc.) and should be validated with intake_layer_inventory.py
    instead of this handoff validator.
    """
    # Filename heuristic
    basename = os.path.basename(path).lower()
    if u"index" in basename or u"ux_handoff_index" in basename:
        return True

    # Section heuristic: index has "交互稿清单与进度" which handoffs never have
    headings = collect_headings(text)
    for _, heading in headings:
        if u"交互稿清单与进度" in heading or u"待确认项汇总" in heading:
            return True

    return False


def validate(path, dsl_path=None):
    errors = []
    warnings = []

    if not os.path.isfile(path):
        return [u"File not found: {0}".format(path)], warnings

    text = read_text(path)

    if _looks_like_index(text, path):
        emit(u"INFO: This appears to be a UX handoff index file ({0}).".format(
            os.path.basename(path)))
        emit(u"INFO: Index files should be validated with: "
             u"python intake_layer_inventory.py validate --index <path>")
        return errors, warnings

    headings = collect_headings(text)
    is_global = handoff_looks_global_or_shared(text)

    # Sections that global handoffs are allowed to skip or replace per template
    GLOBAL_EXEMPT_SECTIONS = [
        u"交互对象清单",
        u"全局/跨页规则",
        u"与视觉稿协作说明",
    ]
    # Global §2 can be "规则协议语义" instead of "页面语义卡"
    GLOBAL_SECTION_ALIASES = {
        u"页面语义卡": [u"规则协议语义"],
    }

    for section in REQUIRED_SECTIONS:
        if not has_section(headings, section):
            # Check if a global alias satisfies the requirement
            alias_satisfied = False
            if is_global and section in GLOBAL_SECTION_ALIASES:
                for alias in GLOBAL_SECTION_ALIASES[section]:
                    if has_section(headings, alias):
                        alias_satisfied = True
                        break
            if alias_satisfied:
                continue

            if is_global and section in GLOBAL_EXEMPT_SECTIONS:
                continue
            if is_global and section == u"状态模型":
                warnings.append(
                    u"Global handoff missing optional section: {0} (fill if state machine exists)".format(section)
                )
                continue
            errors.append(u"Missing required section: {0}".format(section))

    for term in REQUIRED_TERMS:
        if term not in text:
            warnings.append(u"Missing recommended traceability term: {0}".format(term))

    for term in UI_MAPPING_TERMS:
        if term not in text:
            warnings.append(u"Missing recommended UI mapping contract term: {0}".format(term))

    missing_boundary = [term for term in BOUNDARY_TERMS if term not in text]
    if missing_boundary:
        errors.append(
            u"Boundary-state matrix is incomplete or unnamed: {0}".format(
                u", ".join(missing_boundary)
            )
        )

    if u"当前代码" in text and u"业务事实" not in text and u"source of truth" not in text:
        warnings.append(
            u"Code-reference boundary is not explicit; state that code is not business truth."
        )

    if u"待确认" not in text:
        errors.append(u"Missing pending-confirmation tracking.")

    validate_table_headers(text, errors)
    validate_business_rules(text, errors, warnings)
    validate_state_transitions(text, warnings)
    validate_pending_items(text, errors)
    validate_feedback_copy(text, warnings)
    validate_page_global_ownership(text, warnings)

    # ---- SEMANTIC layer checks ----
    validate_rule_granularity(text, errors)
    validate_sub_component_coverage(text, warnings)
    validate_change_record(text, errors, warnings)

    # ---- NEW: Mermaid validation (2026-05-26) ----
    validate_mermaid_syntax(text, errors)          # T1+T2 ERROR
    validate_mermaid_reachability(text, warnings)   # T3 WARN

    # ---- NEW: DSL-aware checks (2026-05-26) ----
    validate_dsl_aware_checks(text, dsl_path, warnings)

    return errors, warnings


def emit(text):
    """兼容 Python 3 + Windows GBK 终端的 Unicode 安全输出。"""
    try:
        print(text)
    except UnicodeEncodeError:
        if hasattr(sys.stdout, "buffer"):
            sys.stdout.buffer.write(text.encode("utf-8", errors="replace") + b"\n")
        else:
            print(text.encode("ascii", errors="replace").decode("ascii"))


def main(argv):
    parser = argparse.ArgumentParser(description="Validate UX handoff markdown.")
    parser.add_argument("handoff", help="Path to UX handoff markdown.")
    parser.add_argument(
        "--dsl",
        default=None,
        help="Optional path to trimmed DSL JSON for advanced checks "
             "(Mermaid scene detection, INSTANCE component resolution)."
    )
    args = parser.parse_args(argv)

    errors, warnings = validate(args.handoff, dsl_path=args.dsl)

    for warning in warnings:
        emit(u"WARN: {0}".format(warning))
    for error in errors:
        emit(u"ERROR: {0}".format(error))

    if errors:
        emit(u"FAIL")
        return 1

    emit(u"PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
