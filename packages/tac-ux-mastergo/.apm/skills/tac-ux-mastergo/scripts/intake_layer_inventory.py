#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""intake_layer_inventory.py -- 整理多链接 MasterGo 交互稿清单。

当用户提供多个 MasterGo 交互稿链接时，本脚本负责：
  parse   -- 解析链接列表，去重、分类、生成清单草案
  validate -- 校验已确认的清单，检查重复和缺失字段

输出格式：page_inventory_draft.md（Markdown 表格）

兼容 Python 3.3+。Python 2.7 不再支持（ur"" 语法已移除）。
"""

from __future__ import print_function

import argparse
import io
import json
import os
import re
import sys

# 版本守卫：Python 2 不再受支持
if sys.version_info[0] < 3:
    sys.stderr.write("ERROR: intake_layer_inventory.py requires Python 3.3+. "
                     "Current: Python {0}\n".format(sys.version.split()[0]))
    sys.exit(1)

# ---------------------------------------------------------------------------
# URL 解析
# ---------------------------------------------------------------------------

# MasterGo URL 格式：
#   https://mastergo.com/file/{file_id}?layer_id={layer_id}
#   https://mastergo.com/file/{file_id}/?layer_id={layer_id}
URL_PATTERN = re.compile(
    r"(?:mastergo|uxd\.tinnove)\.com(?:\.cn)?/file/(?P<file_id>[^/?]+).*[?&]layer_id=(?P<layer_id>[^&\s]+)"
)


def parse_url(url):
    """从 MasterGo URL 中提取 file_id 和 layer_id。

    返回：
      (file_id, layer_id) 或 None（解析失败）
    """
    match = URL_PATTERN.search(url)
    if not match:
        return None
    return match.group("file_id"), match.group("layer_id")


# ---------------------------------------------------------------------------
# 类型初判
# ---------------------------------------------------------------------------

# 分类关键词正则（Python 3: 所有字符串均为 unicode，不再需要 ur 前缀）
_TYPE_PATTERNS = [
    (u"弹窗/浮层", re.compile(
        r"popup|dialog|modal|alert|toast|snackbar|action[-_]?sheet|bottom[-_]?sheet|picker|"
        r"popover|tooltip|confirm|overlay|banner|notification|"
        r"\u5f39\u7a97|\u5bf9\u8bdd\u6846|\u786e\u8ba4|\u63d0\u793a\u6846|\u901a\u77e5|"
        r"\u6d6e\u5c42|\u6d6e\u7a97|\u63d0\u793a",
        re.IGNORECASE | re.UNICODE,
    )),
    (u"半屏/面板", re.compile(
        r"half[-_]?screen|halfscreen|panel|drawer|"
        r"\u534a\u5c41|\u62bd\u5c49|\u9762\u677f",
        re.IGNORECASE | re.UNICODE,
    )),
    (u"全局/共享规则", re.compile(
        r"global|shared|common|rule|protocol|task|recovery|sync|"
        r"network|cross[-_]?page|permission|account|"
        r"\u5168\u5c40|\u5171\u4eab|\u901a\u7528|\u89c4\u5219|\u534f\u8bae|\u4efb\u52a1|"
        r"\u6062\u590d|\u540c\u6b65|\u8de8\u9875",
        re.IGNORECASE | re.UNICODE,
    )),
    (u"说明/文档区", re.compile(
        r"readme|doc|guide|intro|about|changelog|cover|index|toc|"
        r"\u8bf4\u660e|\u4ecb\u7ecd|\u6587\u6863|\u76ee\u5f55|\u7d22\u5f15|\u5c01\u9762|"
        r"\u66f4\u65b0\u65e5\u5fd7|\u9898\u7eb2",
        re.IGNORECASE | re.UNICODE,
    )),
]


def classify_layer(name, file_id, layer_id):
    """根据名称、file_id、layer_id 做初步类型分类。

    返回：
      (类型标签, 是否建议纳入分析, 备注)
    """
    search_text = name or u"{0}/{1}".format(file_id, layer_id)

    for label, pattern in _TYPE_PATTERNS:
        if pattern.search(search_text):
            if label == u"说明/文档区":
                return (label, u"\u274c", u"\u7591\u4f3c\u8bf4\u660e\u533a/\u6587\u6863\uff0c\u975e\u4ea4\u4e92\u9875\u9762")  # 疑似说明区/文档，非交互页面
            if label == u"弹窗/浮层":
                return (label, u"\u2705", u"")
            if label == u"半屏/面板":
                return (label, u"\u2705", u"")
            if label == u"全局/共享规则":
                return (label, u"\u2705", u"\u4f9d\u8d56\u5168\u5c40\u89c4\u5219")  # 依赖全局规则
            return (label, u"\u2705", u"")

    # 默认视为页面
    return (u"\u9875\u9762", u"\u2705", u"")  # 页面


# ---------------------------------------------------------------------------
# 清单生成
# ---------------------------------------------------------------------------

def _to_unicode(s):
    """确保返回 str（Python 3 兼容，保留函数签名以避免调用方修改）。"""
    if s is None:
        return ""
    if isinstance(s, bytes):
        return s.decode("utf-8", errors="replace")
    return s


def build_inventory(links, names=None):
    """从链接列表构建清单数据结构。

    参数：
      links: [(file_id, layer_id, raw_url), ...]
      names: dict 或 None，{layer_id: name} 的映射

    返回：
      [{"编号": ..., "名称": ..., "file_id": ..., "layer_id": ...,
         "类型初判": ..., "建议纳入": ..., "备注": ...}, ...]
    """
    seen = set()
    rows = []
    counter = 0

    for file_id, layer_id, raw_url in links:
        key = (file_id, layer_id)

        if key in seen:
            continue

        seen.add(key)
        counter += 1

        display_name = u""
        if names and layer_id in names:
            display_name = _to_unicode(names[layer_id])
        elif names and layer_id not in names:
            display_name = u"\uff08\u540d\u79f0\u672a\u63d0\u4f9b\uff09"  # （名称未提供）

        category, recommendation, note = classify_layer(display_name, file_id, layer_id)

        row = {
            u"编号": _to_unicode(str(counter)),
            u"名称": display_name,
            u"file_id": file_id,
            u"layer_id": layer_id,
            u"类型初判": category,
            u"是否建议纳入分析": recommendation,
            u"备注": note,
        }
        rows.append(row)

    return rows


def render_inventory_table(inventory):
    """将清单渲染为 Markdown 表格字符串（导航表，可嵌入 ux_handoff_index.md）。

    返回：unicode 字符串。
    """
    columns = [
        u"编号",
        u"名称",
        u"file_id",
        u"layer_id",
        u"类型初判",
        u"是否建议纳入分析",
        u"备注",
    ]

    lines = []
    lines.append(u"## 交互稿导航（草案）")
    lines.append(u"")
    lines.append(
        u"> 由 `intake_layer_inventory.py parse` 自动生成。"
        u"请逐项确认分析范围，确认后本表将作为 `ux_handoff_index.md` 的导航表。"
    )
    lines.append(u"")

    # 摘要
    page_count = sum(1 for r in inventory if r[u"类型初判"] == u"页面")
    popup_count = sum(1 for r in inventory if r[u"类型初判"] == u"弹窗/浮层")
    half_count = sum(1 for r in inventory if r[u"类型初判"] == u"半屏/面板")
    global_count = sum(1 for r in inventory if r[u"类型初判"] == u"全局/共享规则")
    doc_count = sum(1 for r in inventory if r[u"类型初判"] == u"说明/文档区")

    lines.append(u"### 摘要")
    lines.append(u"")
    lines.append(u"| 类型 | 数量 |")
    lines.append(u"|------|------|")
    lines.append(u"| 页面 | {0} |".format(page_count))
    lines.append(u"| 弹窗/浮层 | {0} |".format(popup_count))
    lines.append(u"| 半屏/面板 | {0} |".format(half_count))
    lines.append(u"| 全局/共享规则 | {0} |".format(global_count))
    lines.append(u"| 说明/文档区 | {0} |".format(doc_count))
    lines.append(u"| **合计** | **{0}** |".format(len(inventory)))
    lines.append(u"")

    # 表格头
    header = u"| " + u" | ".join(columns) + u" |"
    separator = u"|" + u"|".join([u"------"] * len(columns)) + u"|"
    lines.append(header)
    lines.append(separator)

    for row in inventory:
        cells = [row.get(col, u"") for col in columns]
        lines.append(u"| " + u" | ".join(cells) + u" |")

    lines.append(u"")

    return u"\n".join(lines)


# ---------------------------------------------------------------------------
# emit -- 兼容 Python 2/3 的 Unicode 输出
# ---------------------------------------------------------------------------

def emit(text):
    """兼容 Python 3 + Windows GBK 终端的 Unicode 安全输出。"""
    try:
        print(text)
    except UnicodeEncodeError:
        # 终端编码不支持当前字符（如 Windows GBK → emoji），退避到 UTF-8 buffer
        if hasattr(sys.stdout, "buffer"):
            sys.stdout.buffer.write(text.encode("utf-8", errors="replace") + b"\n")
        else:
            print(text.encode("ascii", errors="replace").decode("ascii"))


# ---------------------------------------------------------------------------
# 子命令：parse
# ---------------------------------------------------------------------------

def cmd_parse(args):
    """解析链接列表文件，生成清单草案。"""
    links_path = args.links

    if not os.path.isfile(links_path):
        emit("RESULT: error")
        emit("REASON: links file not found: {0}".format(links_path))
        return 1

    # 读取链接列表
    with io.open(links_path, "r", encoding="utf-8") as handle:
        raw_lines = handle.readlines()

    parsed_links = []
    parse_errors = []
    seen_dup = set()

    for line_num, line in enumerate(raw_lines, 1):
        stripped = line.strip()
        # 跳过空行和注释行
        if not stripped or stripped.startswith("#"):
            continue

        result = parse_url(stripped)
        if result is None:
            parse_errors.append(u"  line {0}: could not parse URL: {1}".format(line_num, stripped[:80]))
            continue

        file_id, layer_id = result
        key = (file_id, layer_id)

        if key in seen_dup:
            continue

        seen_dup.add(key)
        parsed_links.append((file_id, layer_id, stripped))

    if parse_errors:
        for err in parse_errors:
            emit(u"WARN: {0}".format(err))
        emit("")

    if not parsed_links:
        emit("RESULT: error")
        emit("REASON: no valid links found in input file")
        return 1

    # 加载名称映射（可选）
    names = {}
    if args.names:
        try:
            with io.open(args.names, "r", encoding="utf-8") as handle:
                raw_names = json.loads(handle.read())
            names = raw_names
        except (ValueError, IOError) as exc:
            emit(u"WARN: names file could not be loaded: {0}".format(exc))

    # 构建清单
    inventory = build_inventory(parsed_links, names)

    # 输出导航表到 stdout，由 AI agent 写入 ux_handoff_index.md
    table = render_inventory_table(inventory)
    emit("---INVENTORY_TABLE_START---")
    for line in table.split("\n"):
        emit(line)
    emit("---INVENTORY_TABLE_END---")

    emit("RESULT: ok")
    emit("TOTAL_LINKS: {0}".format(len(raw_lines)))
    emit("VALID_LINKS: {0}".format(len(parsed_links)))
    emit("UNIQUE_ITEMS: {0}".format(len(inventory)))

    summary = {}
    for row in inventory:
        cat = row[u"类型初判"]
        summary[cat] = summary.get(cat, 0) + 1
    for cat, count in sorted(summary.items()):
        emit(u"  {0}: {1}".format(cat, count))

    return 0


# ---------------------------------------------------------------------------
# 子命令：validate
# ---------------------------------------------------------------------------

def cmd_validate(args):
    """校验 ux_handoff_index.md 的结构完整性。"""
    index_path = args.index

    if not os.path.isfile(index_path):
        emit("RESULT: error")
        emit("REASON: index file not found: {0}".format(index_path))
        return 1

    with io.open(index_path, "r", encoding="utf-8") as handle:
        content = handle.read()

    errors = []
    warnings = []

    base_dir = os.path.dirname(os.path.abspath(index_path))

    # ---- 1. Parse tables from index ----
    tables = _parse_markdown_tables(content)

    # ---- 2. Validate §1 交互稿清单与进度 ----
    section1_tables = _find_all_tables_by_header(tables, [u"编号", u"名称", u"file_id", u"layer_id"])
    if not section1_tables:
        errors.append(u"§1 交互稿清单：未找到包含 编号/名称/file_id/layer_id 的表格")
    else:
        for s1t in section1_tables:
            _validate_section1(s1t, errors, warnings, base_dir)

    # ---- 3. Validate §2 全局/跨页规则 ----
    section2_table = _find_table_by_header(tables, [u"规则摘要", u"类型", u"归属"])
    if section2_table is None:
        errors.append(u"§2 全局/跨页规则：未找到包含 规则摘要/类型/归属 的表格")
    else:
        _validate_section2(section2_table, errors, warnings)

    # ---- 4. Validate §3 待确认项汇总 ----
    section3_table = _find_table_by_header(tables, [u"编号", u"所属 handoff", u"阻塞级别", u"状态"])
    if section3_table is None:
        errors.append(u"§3 待确认项汇总：未找到包含 编号/所属 handoff/阻塞级别/状态 的表格")
    else:
        _validate_section3(section3_table, errors, warnings, base_dir)

    # ---- 5. Cross-check: directory files vs index registrations ----
    _cross_check_directory(base_dir, section1_tables if section1_tables else [], section2_table, errors, warnings)

    # ---- 输出 ----
    for warning in warnings:
        emit(u"WARN: {0}".format(warning))
    for error in errors:
        emit(u"ERROR: {0}".format(error))

    if errors:
        emit("RESULT: FAIL")
        return 1

    if warnings:
        emit("RESULT: PASS (with warnings)")
    else:
        emit("RESULT: PASS")
    return 0


# ---------------------------------------------------------------------------
# 辅助：Markdown 表解析
# ---------------------------------------------------------------------------

def _parse_markdown_tables(text):
    """Parse all Markdown tables from text, returning list of {header, rows} dicts."""
    tables = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("|") and line.endswith("|"):
            # Start of a table
            header_cells = [c.strip() for c in line.strip("|").split("|")]
            i += 1
            # Skip separator row
            if i < len(lines):
                sep = lines[i].strip()
                if re.match(r"^\|[\s:|-]+\|$", sep):
                    i += 1
            rows = []
            while i < len(lines):
                row_line = lines[i].strip()
                if not (row_line.startswith("|") and row_line.endswith("|")):
                    break
                cells = [c.strip() for c in row_line.strip("|").split("|")]
                rows.append(cells)
                i += 1
            tables.append({"header": header_cells, "rows": rows})
        else:
            i += 1
    return tables


def _find_table_by_header(tables, required_columns):
    """Find first table containing all required columns."""
    for table in tables:
        if all(col in table["header"] for col in required_columns):
            return table
    return None


def _find_all_tables_by_header(tables, required_columns):
    """Find ALL tables containing all required columns (for sub-section tables like 1.1, 1.2, ...)."""
    results = []
    for table in tables:
        if all(col in table["header"] for col in required_columns):
            results.append(table)
    return results


def _row_dict(header, row):
    """Convert a table row to a dict keyed by header."""
    result = {}
    for idx, key in enumerate(header):
        result[key] = row[idx].strip() if idx < len(row) else u""
    return result


def _non_empty_rows(table):
    """Return rows that have at least one non-empty cell."""
    return [row for row in table["rows"] if any(c.strip() for c in row)]


# ---------------------------------------------------------------------------
# §1 校验
# ---------------------------------------------------------------------------

def _validate_section1(table, errors, warnings, base_dir):
    """Validate §1 交互稿清单."""
    # Check required columns
    required_cols = [
        u"编号", u"名称", u"MasterGo 源链接", u"file_id", u"layer_id",
        u"类型初判", u"是否建议纳入分析", u"状态", u"产物文件", u"依赖", u"备注",
    ]
    missing = [c for c in required_cols if c not in table["header"]]
    if missing:
        errors.append(u"§1 交互稿清单缺少列: {0}".format(u", ".join(missing)))

    # Validate rows
    valid_statuses = {u"⏳ pending", u"✅ done", u"⏭️ skipped"}
    valid_recommendations = {u"✅", u"❌"}
    valid_types = {u"页面", u"弹窗", u"弹窗/浮层", u"半屏", u"半屏/面板",
                   u"全局/共享规则", u"说明/文档区"}

    duplicate_ids = set()
    seen_ids = set()
    done_without_file = []

    for row_num, row in enumerate(_non_empty_rows(table), 1):
        d = _row_dict(table["header"], row)
        item_id = d.get(u"编号", u"")

        # Duplicate check
        if item_id and item_id in seen_ids:
            duplicate_ids.add(item_id)
        seen_ids.add(item_id)

        # Status validation
        status = d.get(u"状态", u"")
        if status and status not in valid_statuses:
            warnings.append(u"§1 行{0}: 无效状态值 '{1}'，期望 {2}"
                           .format(row_num, status, u"/".join(valid_statuses)))

        # Recommendation validation
        rec = d.get(u"是否建议纳入分析", u"")
        if rec and rec not in valid_recommendations:
            warnings.append(u"§1 行{0}: 无效'是否建议纳入分析'值 '{1}'"
                           .format(row_num, rec))

        # Type validation
        typ = d.get(u"类型初判", u"")
        if typ and typ not in valid_types:
            warnings.append(u"§1 行{0}: 未识别的类型初判 '{1}'"
                           .format(row_num, typ))

        # Done status must have 产物文件
        if status == u"✅ done":
            artifact = d.get(u"产物文件", u"").strip().strip("`")
            # 合法豁免：空值 / 占位符 / 父节点（子实体各自持有产物文件）
            if not artifact or artifact.strip() in (u"", u"—"):
                done_without_file.append(item_id or u"行{0}".format(row_num))
            elif artifact.strip() == u"包含多个子实体":
                pass  # 父节点，子实体各自承担产物文件，无需警告
            else:
                # Check file exists
                file_path = os.path.join(base_dir, artifact.strip())
                if not os.path.isfile(file_path):
                    warnings.append(u"§1 行{0}: 产物文件 '{1}' 不存在"
                                   .format(row_num, artifact))

    if duplicate_ids:
        errors.append(u"§1: 重复编号: {0}".format(u", ".join(sorted(duplicate_ids))))
    if done_without_file:
        warnings.append(u"§1: ✅ done 条目缺少产物文件: {0}"
                       .format(u", ".join(done_without_file)))


# ---------------------------------------------------------------------------
# §2 校验
# ---------------------------------------------------------------------------

def _validate_section2(table, errors, warnings):
    """Validate §2 全局/跨页规则."""
    required_cols = [u"规则摘要", u"类型", u"影响范围", u"归属", u"状态", u"来源", u"参见"]
    missing = [c for c in required_cols if c not in table["header"]]
    if missing:
        errors.append(u"§2 全局/跨页规则缺少列: {0}".format(u", ".join(missing)))

    valid_types = {u"simple", u"complex"}
    valid_ownership = {u"page", u"shared", u"global"}
    valid_statuses = {u"confirmed", u"candidate", u"pending"}

    for row_num, row in enumerate(_non_empty_rows(table), 1):
        d = _row_dict(table["header"], row)
        rule_type = d.get(u"类型", u"").strip().lower()

        if rule_type and rule_type not in valid_types:
            warnings.append(u"§2 行{0}: 无效类型 '{1}'，期望 simple/complex"
                           .format(row_num, rule_type))

        ownership = d.get(u"归属", u"").strip().lower()
        if ownership and ownership not in valid_ownership:
            warnings.append(u"§2 行{0}: 无效归属 '{1}'，期望 page/shared/global"
                           .format(row_num, ownership))

        status = d.get(u"状态", u"").strip().lower()
        if status and status not in valid_statuses:
            warnings.append(u"§2 行{0}: 无效状态 '{1}'，期望 confirmed/candidate/pending"
                           .format(row_num, status))

        # complex MUST have 参见
        if rule_type == u"complex":
            see_also = d.get(u"参见", u"").strip()
            if not see_also:
                warnings.append(u"§2 行{0}: complex 规则缺少 '参见' 字段"
                               .format(row_num))


# ---------------------------------------------------------------------------
# §3 校验
# ---------------------------------------------------------------------------

def _validate_section3(table, errors, warnings, base_dir):
    """Validate §3 待确认项汇总."""
    required_cols = [
        u"编号", u"所属 handoff", u"问题摘要", u"确认角色", u"跑偏风险",
        u"阻塞级别", u"推荐选项", u"可继续假设", u"建议确认时机", u"影响范围", u"状态",
    ]
    missing = [c for c in required_cols if c not in table["header"]]
    if missing:
        errors.append(u"§3 待确认项汇总缺少列: {0}".format(u", ".join(missing)))

    valid_roles = {u"product", u"interaction", u"visual", u"technical", u"host", u"data", u"mixed"}
    valid_risks = {u"state", u"data", u"navigation", u"effect", u"ownership",
                   u"ui-carrier", u"acceptance", u"none"}
    valid_levels = {u"pre-blocking", u"blocking", u"non-blocking"}
    valid_timing = {u"now", u"before-implementation", u"before-visual-landing", u"later"}
    valid_pending_status = {u"open", u"resolved"}

    seen_ids = set()
    duplicate_ids = set()
    handoff_refs = set()

    for row_num, row in enumerate(_non_empty_rows(table), 1):
        d = _row_dict(table["header"], row)
        item_id = d.get(u"编号", u"")

        if item_id and item_id in seen_ids:
            duplicate_ids.add(item_id)
        seen_ids.add(item_id)

        handoff = d.get(u"所属 handoff", u"").strip().strip("`")
        if handoff:
            handoff_refs.add(handoff)

        role = d.get(u"确认角色", u"").strip().lower()
        if role and role not in valid_roles:
            warnings.append(u"§3 行{0}: 无效确认角色 '{1}'".format(row_num, role))

        risk = d.get(u"跑偏风险", u"").strip().lower()
        if risk and risk not in valid_risks:
            warnings.append(u"§3 行{0}: 无效跑偏风险 '{1}'".format(row_num, risk))

        level = d.get(u"阻塞级别", u"").strip().lower()
        # Allow ~~strikethrough~~ for resolved items
        clean_level = re.sub(r"~~", "", level).strip()
        if clean_level and clean_level not in valid_levels:
            if level not in valid_levels:
                warnings.append(u"§3 行{0}: 无效阻塞级别 '{1}'".format(row_num, level))

        # 先取状态，供后续 timing 检查判断是否 resolved
        pending_status = d.get(u"状态", u"").strip().lower()

        timing = d.get(u"建议确认时机", u"").strip().lower()
        # 已 resolved 条目用 '—' 占位是合法的（无需确认时机）
        if timing and timing not in valid_timing and pending_status != u"resolved":
            warnings.append(u"§3 行{0}: 无效建议确认时机 '{1}'".format(row_num, timing))

        if pending_status and pending_status not in valid_pending_status:
            warnings.append(u"§3 行{0}: 无效状态 '{1}'，期望 open/resolved"
                           .format(row_num, pending_status))

    if duplicate_ids:
        errors.append(u"§3: 重复编号: {0}".format(u", ".join(sorted(duplicate_ids))))

    # Cross-reference check
    for ref in handoff_refs:
        ref_path = os.path.join(base_dir, ref)
        if not os.path.isfile(ref_path):
            warnings.append(u"§3: handoff 文件 '{0}' 不存在".format(ref))


# ---------------------------------------------------------------------------
# §5 交叉校验：目录文件 vs Index 登记
# ---------------------------------------------------------------------------

def _cross_check_directory(base_dir, section1_tables, section2_table, errors, warnings):
    """Cross-check all ux_handoff_*.md files in directory against Index registrations.

    Checks:
      - Files present in directory but NOT registered in Index (§1 or §2) → ERROR
      - Files registered in §1 as ✅ done but NOT present in directory → WARNING
      - Total file count mismatch between directory and registered files → WARNING

    Args:
      section1_tables: list of table dicts (may be empty) from §1 sub-sections
      section2_table: single table dict or None from §2
    """
    # Enumerate all handoff files in the directory (excluding index itself)
    try:
        dir_files = sorted([
            f for f in os.listdir(base_dir)
            if f.startswith(u"ux_handoff_") and f.endswith(u".md")
               and f != u"ux_handoff_index.md"
        ])
    except OSError:
        return  # cannot list directory, skip cross-check

    if not dir_files:
        return  # no handoff files to cross-check

    # Collect registered file names from §1 (aggregate across all sub-tables)
    registered_files = set()
    if section1_tables:
        for table in section1_tables:
            for row in _non_empty_rows(table):
                d = _row_dict(table["header"], row)
                artifact = d.get(u"产物文件", u"").strip().strip("`")
                if artifact and artifact not in (u"—", u""):
                    for part in _split_artifact(artifact):
                        registered_files.add(part)

    # Collect referenced files from §2 (complex rules → 参见 column)
    if section2_table is not None:
        for row in _non_empty_rows(section2_table):
            d = _row_dict(section2_table["header"], row)
            rule_type = d.get(u"类型", u"").strip().lower()
            if rule_type == u"complex":
                see_also = d.get(u"参见", u"").strip().strip("`")
                if see_also and see_also not in (u"—", u""):
                    for part in _split_artifact(see_also):
                        registered_files.add(part)

    # Check: files in directory but not registered → ERROR (potential orphan)
    unregistered = [f for f in dir_files if f not in registered_files]
    if unregistered:
        errors.append(
            u"交叉校验：目录中存在未在 Index 登记的 handoff 文件 — "
            u"这些文件可能来自其他已被覆写的会话，需合并到 Index：{0}".format(
                u", ".join(sorted(unregistered))
            )
        )

    # Check: registered files that don't exist in directory → WARNING
    missing = [f for f in registered_files if f not in dir_files]
    if missing:
        warnings.append(
            u"交叉校验：Index 登记但文件不存在的 handoff：{0}".format(
                u", ".join(sorted(missing))
            )
        )

    # Check: §1 ✅ done count vs directory file count
    if section1_tables:
        done_count = 0
        for table in section1_tables:
            for row in _non_empty_rows(table):
                d = _row_dict(table["header"], row)
                if d.get(u"状态", u"") == u"✅ done":
                    done_count += 1

        if len(dir_files) != len(registered_files):
            warnings.append(
                u"交叉校验：目录中 handoff 文件数 ({0}) ≠ Index 登记的产物文件数 ({1})，"
                u"可能存在 Index 未完全合并的会话产物".format(
                    len(dir_files), len(registered_files)
                )
            )


def _split_artifact(text):
    """Split artifact field that may contain multiple files.

    Handles separators: / , space, newline.
    Returns list of non-empty strings.
    """
    if not text:
        return []
    parts = []
    for part in re.split(r"[/,，\s]+", text):
        part = part.strip().strip("`")
        if part and part not in (u"—", u""):
            parts.append(part)
    return parts


# ---------------------------------------------------------------------------
# merge 子命令
# ---------------------------------------------------------------------------

def _extract_section(content, section_number, section_name_hint=None):
    """Extract a Markdown section block (## N. Title) from content.

    Returns (title_line, heading_level, body_text) or (None, None, None).
    section_number: e.g. "1", "2", "3"
    """
    pattern = r"^##\s+" + re.escape(section_number) + r"\..*$"
    lines = content.split("\n")
    start = None
    title = None

    for i, line in enumerate(lines):
        if re.match(pattern, line.strip()):
            start = i
            title = line.strip()
            break

    if start is None:
        return None, None, None

    # Find end: next ## section or EOF
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if re.match(r"^##\s+\d+\.", lines[i].strip()):
            end = i
            break

    body = "\n".join(lines[start + 1:end])
    # Determine heading level from title
    level_match = re.match(r"^##\s+(\d+)\.", title)
    level = level_match.group(1) if level_match else section_number

    return title, level, body


def _parse_section1_rows(body):
    """Parse ALL §1 sub-tables, returning aggregated list of dicts keyed by header."""
    if not body:
        return []
    tables = _parse_markdown_tables(body)
    section1_tables = _find_all_tables_by_header(
        tables, [u"编号", u"名称", u"file_id", u"layer_id"]
    )
    all_rows = []
    for table in section1_tables:
        all_rows.extend([
            _row_dict(table["header"], row)
            for row in _non_empty_rows(table)
        ])
    return all_rows


def _parse_section2_rows(body):
    """Parse §2 table rows, returning list of dicts keyed by header."""
    if not body:
        return []
    tables = _parse_markdown_tables(body)
    section2_tables = _find_all_tables_by_header(
        tables, [u"规则摘要", u"类型", u"归属"]
    )
    all_rows = []
    for table in section2_tables:
        all_rows.extend([
            _row_dict(table["header"], row)
            for row in _non_empty_rows(table)
        ])
    return all_rows


def _parse_section3_rows(body):
    """Parse §3 table rows, returning list of dicts keyed by header."""
    if not body:
        return []
    tables = _parse_markdown_tables(body)
    section3_tables = _find_all_tables_by_header(
        tables, [u"编号", u"所属 handoff", u"阻塞级别", u"状态"]
    )
    all_rows = []
    for table in section3_tables:
        all_rows.extend([
            _row_dict(table["header"], row)
            for row in _non_empty_rows(table)
        ])
    return all_rows


def cmd_merge(args):
    """Merge two ux_handoff_index.md files, deduplicating and reporting changes.

    Strategy:
      - §1: deduplicate by 编号; incoming rows win for same 编号
      - §2: deduplicate by 规则摘要 (exact match); existing wins
      - §3: deduplicate by 编号; incoming wins for same 编号

    Outputs a diff-like report for AI to apply via replace_in_file.
    Does NOT modify files directly — the report is human/AI-actionable.
    """
    existing_path = args.existing
    incoming_path = args.incoming

    if not os.path.isfile(existing_path):
        emit("RESULT: error")
        emit("REASON: existing index not found: {0}".format(existing_path))
        return 1

    if not os.path.isfile(incoming_path):
        emit("RESULT: error")
        emit("REASON: incoming index not found: {0}".format(incoming_path))
        return 1

    with io.open(existing_path, "r", encoding="utf-8") as f:
        existing_content = f.read()
    with io.open(incoming_path, "r", encoding="utf-8") as f:
        incoming_content = f.read()

    # ---- §1: 交互稿清单 ----
    _, _, s1_existing = _extract_section(existing_content, "1")
    _, _, s1_incoming = _extract_section(incoming_content, "1")
    existing_s1 = _parse_section1_rows(s1_existing) if s1_existing else []
    incoming_s1 = _parse_section1_rows(s1_incoming) if s1_incoming else []

    existing_ids_s1 = {r.get(u"编号", u"") for r in existing_s1}
    incoming_ids_s1 = {r.get(u"编号", u"") for r in incoming_s1}

    new_s1 = [r for r in incoming_s1 if r.get(u"编号", u"") not in existing_ids_s1]
    updated_s1 = [r for r in incoming_s1 if r.get(u"编号", u"") in existing_ids_s1]

    # ---- §2: 全局/跨页规则 ----
    _, _, s2_existing = _extract_section(existing_content, "2")
    _, _, s2_incoming = _extract_section(incoming_content, "2")
    existing_s2 = _parse_section2_rows(s2_existing) if s2_existing else []
    incoming_s2 = _parse_section2_rows(s2_incoming) if s2_incoming else []

    existing_summaries = {r.get(u"规则摘要", u"") for r in existing_s2}
    new_s2 = [r for r in incoming_s2 if r.get(u"规则摘要", u"") not in existing_summaries]
    matched_s2 = [r for r in incoming_s2 if r.get(u"规则摘要", u"") in existing_summaries]

    # ---- §3: 待确认项汇总 ----
    _, _, s3_existing = _extract_section(existing_content, "3")
    _, _, s3_incoming = _extract_section(incoming_content, "3")
    existing_s3 = _parse_section3_rows(s3_existing) if s3_existing else []
    incoming_s3 = _parse_section3_rows(s3_incoming) if s3_incoming else []

    existing_ids_s3 = {r.get(u"编号", u"") for r in existing_s3}
    new_s3 = [r for r in incoming_s3 if r.get(u"编号", u"") not in existing_ids_s3]
    updated_s3 = [r for r in incoming_s3 if r.get(u"编号", u"") in existing_ids_s3]

    # ---- Report ----
    emit("---MERGE_REPORT_START---")
    emit("")
    emit("## Merge Summary")
    emit("")
    emit("| Section | Existing | Incoming | New (to add) | Updated (to replace) | Already present |")
    emit("|:--|:--|:--|:--|:--|:--|")
    emit("| §1 交互稿清单 | {0} | {1} | {2} | {3} | {4} |".format(
        len(existing_s1), len(incoming_s1), len(new_s1),
        len(updated_s1), len(incoming_s1) - len(new_s1)
    ))
    emit("| §2 全局规则 | {0} | {1} | {2} | {3} | {4} |".format(
        len(existing_s2), len(incoming_s2), len(new_s2),
        0, len(matched_s2)
    ))
    emit("| §3 待确认项 | {0} | {1} | {2} | {3} | {4} |".format(
        len(existing_s3), len(incoming_s3), len(new_s3),
        len(updated_s3), len(incoming_s3) - len(new_s3) - len(updated_s3)
    ))
    emit("")

    if new_s1:
        emit("### §1 — New entries to ADD")
        emit("")
        emit("| 编号 | 名称 | file_id | layer_id | 类型初判 | 产物文件 |")
        emit("|:--|:--|:--|:--|:--|:--|")
        for r in new_s1:
            emit("| {0} | {1} | {2} | {3} | {4} | {5} |".format(
                r.get(u"编号", u""),
                r.get(u"名称", u""),
                r.get(u"file_id", u""),
                r.get(u"layer_id", u""),
                r.get(u"类型初判", u""),
                r.get(u"产物文件", u""),
            ))
        emit("")

    if updated_s1:
        emit("### §1 — Entries to UPDATE (incoming wins)")
        emit("")
        for r in updated_s1:
            emit("- `{0}` ({1})".format(r.get(u"编号", u""), r.get(u"名称", u"")))
        emit("")

    if new_s2:
        emit("### §2 — New global rules to ADD")
        emit("")
        emit("| 规则摘要 | 类型 | 归属 | 参见 |")
        emit("|:--|:--|:--|:--|")
        for r in new_s2:
            emit("| {0} | {1} | {2} | {3} |".format(
                r.get(u"规则摘要", u""),
                r.get(u"类型", u""),
                r.get(u"归属", u""),
                r.get(u"参见", u""),
            ))
        emit("")

    if new_s3:
        emit("### §3 — New pending items to ADD")
        emit("")
        emit("| 编号 | 所属 handoff | 问题摘要 | 阻塞级别 |")
        emit("|:--|:--|:--|:--|")
        for r in new_s3:
            emit("| {0} | {1} | {2} | {3} |".format(
                r.get(u"编号", u""),
                r.get(u"所属 handoff", u""),
                r.get(u"问题摘要", u"")[:60],
                r.get(u"阻塞级别", u""),
            ))
        emit("")

    if updated_s3:
        emit("### §3 — Pending items to UPDATE (incoming wins)")
        emit("")
        for r in updated_s3:
            emit("- `{0}`: {1}".format(
                r.get(u"编号", u""),
                r.get(u"问题摘要", u"")[:60],
            ))
        emit("")

    total_new = len(new_s1) + len(new_s2) + len(new_s3)
    total_update = len(updated_s1) + len(updated_s3)

    emit("---MERGE_REPORT_END---")
    emit("")
    emit("RESULT: ok")
    emit("ACTION_REQUIRED: Apply new entries via replace_in_file on existing index.")
    emit("NEW_ENTRIES: {0}".format(total_new))
    emit("UPDATED_ENTRIES: {0}".format(total_update))
    emit("NO_CHANGE: Existing index already contains all incoming entries."
         if total_new == 0 and total_update == 0 else "")

    return 0


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main(argv):
    parser = argparse.ArgumentParser(
        description="Intake and inventory MasterGo interaction links for tac-ux-mastergo."
    )
    subparsers = parser.add_subparsers(dest="command")

    # ---- parse ----
    parse_parser = subparsers.add_parser("parse", help="Parse a link list, emit navigation table to stdout.")
    parse_parser.add_argument("--links", required=True, help="Path to link list file (one URL per line).")
    parse_parser.add_argument(
        "--names",
        default=None,
        help="Optional JSON file mapping layer_id -> display name.",
    )
    parse_parser.set_defaults(func=cmd_parse)

    # ---- validate ----
    validate_parser = subparsers.add_parser("validate", help="Validate navigation table in ux_handoff_index.md.")
    validate_parser.add_argument("--index", required=True, help="Path to ux_handoff_index.md.")
    validate_parser.set_defaults(func=cmd_validate)

    # ---- merge ----
    merge_parser = subparsers.add_parser(
        "merge",
        help="Merge new entries into an existing ux_handoff_index.md. "
             "Deduplicates by 编号 (§1), 规则摘要 (§2), and 编号 (§3). "
             "Reports what would be merged without modifying files — "
             "AI must apply changes via replace_in_file based on the output.",
    )
    merge_parser.add_argument("--existing", required=True,
                              help="Path to existing ux_handoff_index.md.")
    merge_parser.add_argument("--incoming", required=True,
                              help="Path to incoming ux_handoff_index.md (new session output).")
    merge_parser.set_defaults(func=cmd_merge)

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
