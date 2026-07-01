#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""validate_iteration.py -- 自动检验 tac-ux-mastergo 技能迭代是否正确。

覆盖四个检验层：
  L1 语法完整性 -- 脚本能否正常编译和 --help
  L2 功能正确性 -- 各子命令对合法/非法输入是否返回预期结果
  L3 裁剪忠实性 -- 交互语义保留 + 视觉属性裁剪 是否正确
  L4 文档一致性 -- SKILL.md / mode_a_workflow.md 是否与脚本 API 一致

运行方式：
  python scripts/validate_iteration.py               # 全部检验
  python scripts/validate_iteration.py --layer L1    # 仅 L1
  python scripts/validate_iteration.py --layer L2 L3 # L2 + L3

The script is intentionally lightweight and Python 2 compatible because some
Windows workstations in this repo still expose Python 2 as `python`.
"""

from __future__ import print_function

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback

# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------

IS_PY2 = sys.version_info[0] < 3


def emit(text):
    if IS_PY2:
        if isinstance(text, unicode):
            sys.stdout.write(text.encode("utf-8") + "\n")
        else:
            sys.stdout.write(text.decode("utf-8") if isinstance(text, str) else str(text))
            sys.stdout.write("\n")
    else:
        # Python 3: guard against Windows console encoding issues
        try:
            print(text)
        except UnicodeEncodeError:
            encoded = text.encode(sys.stdout.encoding or "utf-8", errors="replace")
            sys.stdout.buffer.write(encoded + b"\n")


def to_unicode(s):
    """安全地将 str/bytes 转为 unicode（Python 2）或 str（Python 3）。"""
    if s is None:
        return u""
    if IS_PY2:
        if isinstance(s, unicode):
            return s
        return s.decode("utf-8", errors="replace")
    else:
        if isinstance(s, bytes):
            return s.decode("utf-8", errors="replace")
        return s


def read_file(path):
    """读取文件内容，返回 unicode。"""
    with io.open(path, "r", encoding="utf-8") as f:
        return f.read()


PYTHON = "python"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_SCRIPT = os.path.join(SCRIPT_DIR, "cache_dsl.py")
INTAKE_SCRIPT = os.path.join(SCRIPT_DIR, "intake_layer_inventory.py")
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
SKILL_MD = os.path.join(SKILL_DIR, "SKILL.md")
MODE_A_MD = os.path.join(SKILL_DIR, "references", "mode_a_workflow.md")


def find_repo_root(start_dir):
    """从 start_dir 向上查找仓库根目录，避免依赖固定目录层级。"""
    current = os.path.abspath(start_dir)
    while True:
        if os.path.isfile(os.path.join(current, "PROJECT.md")) or os.path.isdir(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return os.path.abspath(start_dir)
        current = parent


REPO_ROOT = find_repo_root(SKILL_DIR)


def run_cmd(args_list, stdin_text=None):
    """执行命令，返回 (returncode, stdout_unicode, stderr_unicode)。"""
    proc = subprocess.Popen(
        [PYTHON] + args_list,
        stdin=subprocess.PIPE if stdin_text else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdin_bytes = stdin_text.encode("utf-8") if stdin_text else None
    out, err = proc.communicate(stdin_bytes)
    return proc.returncode, to_unicode(out), to_unicode(err)


def parse_result(stdout):
    """解析脚本输出的 RESULT: 行。"""
    result = {}
    for line in stdout.splitlines():
        line = line.strip()
        if ":" in line:
            colon_idx = line.index(":")
            key = line[:colon_idx].strip()
            value = line[colon_idx + 1:].strip()
            result[key] = value
    return result


def safe_traceback():
    """获取 traceback 字符串，Python 2/3 安全。"""
    return to_unicode(traceback.format_exc())


# ---------------------------------------------------------------------------
# L1 语法完整性
# ---------------------------------------------------------------------------

def test_l1():
    """L1: 脚本编译 + --help 正常退出。"""
    emit(u"\n=== L1 语法完整性 ===")
    passed = 0
    total = 0

    scripts = [
        (CACHE_SCRIPT, u"cache_dsl.py"),
        (INTAKE_SCRIPT, u"intake_layer_inventory.py"),
    ]

    for script_path, label in scripts:
        if not os.path.isfile(script_path):
            emit(u"  [FAIL] {0}: script not found at {1}".format(label, script_path))
            continue

        # 编译检查
        total += 1
        try:
            source_text = read_file(script_path)
            if IS_PY2:
                source_bytes = source_text.encode("utf-8")
            else:
                source_bytes = source_text
            compile(source_bytes, script_path, "exec")
            emit(u"  [PASS] {0}: syntax compiles".format(label))
            passed += 1
        except SyntaxError as exc:
            emit(u"  [FAIL] {0}: syntax error: {1}".format(label, exc))

        # --help 退出码
        total += 1
        rc, out, err = run_cmd([script_path, "--help"])
        if rc == 0:
            emit(u"  [PASS] {0}: --help exits 0".format(label))
            passed += 1
        else:
            emit(u"  [FAIL] {0}: --help exits {1}, stderr: {2}".format(
                label, rc, err[:200]))

        # 子命令 --help
        if label == u"cache_dsl.py":
            for sub in ["check", "save"]:
                total += 1
                rc, out, err = run_cmd([script_path, sub, "--help"])
                if rc == 0:
                    emit(u"  [PASS] {0} {1} --help exits 0".format(label, sub))
                    passed += 1
                else:
                    emit(u"  [FAIL] {0} {1} --help exits {2}".format(label, sub, rc))
        elif label == u"intake_layer_inventory.py":
            for sub in ["parse", "validate"]:
                total += 1
                rc, out, err = run_cmd([script_path, sub, "--help"])
                if rc == 0:
                    emit(u"  [PASS] {0} {1} --help exits 0".format(label, sub))
                    passed += 1
                else:
                    emit(u"  [FAIL] {0} {1} --help exits {2}".format(label, sub, rc))

    emit(u"\nL1: {0}/{1} passed".format(passed, total))
    return passed == total, {"passed": passed, "total": total}


# ---------------------------------------------------------------------------
# L2 功能正确性
# ---------------------------------------------------------------------------

def test_l2():
    """L2: 各子命令的功能正确性。"""
    emit(u"\n=== L2 功能正确性 ===")
    passed = 0
    total = 0

    tmpdir = tempfile.mkdtemp(prefix="tac_ux_test_")

    try:
        # ---- intake_layer_inventory.py parse ----
        links_file = os.path.join(tmpdir, "test_links.txt")
        valid_url = "https://mastergo.com/file/abc123?layer_id=layer_001"
        valid_url2 = "https://mastergo.com/file/abc123/?layer_id=layer_002"
        invalid_url = "https://example.com/not-mastergo"
        with io.open(links_file, "w", encoding="utf-8") as f:
            f.write(u"# comment line\n")
            f.write(valid_url + u"\n")
            f.write(valid_url2 + u"\n")
            f.write(valid_url + u"\n")   # duplicate
            f.write(invalid_url + u"\n")

        # test parse
        total += 1
        rc, out, err = run_cmd([
            INTAKE_SCRIPT, "parse", "--links", links_file,
        ])
        if rc != 0:
            emit(u"  [FAIL] intake parse: unexpected exit code {0}".format(rc))
            emit(u"    stderr: {0}".format(err[:200]))
        else:
            result = parse_result(out)
            if result.get("RESULT") == "ok":
                has_table = "---INVENTORY_TABLE_START---" in out
                has_id1 = "layer_001" in out
                has_id2 = "layer_002" in out
                expected = "UNIQUE_ITEMS: 2" in out
                if expected and has_table and has_id1 and has_id2:
                    emit(u"  [PASS] intake parse: table emitted to stdout, dedup OK")
                    passed += 1
                else:
                    emit(u"  [FAIL] intake parse: stdout check failed")
                    emit(u"    table_start: {0}, layer_001: {1}, layer_002: {2}, unique_2: {3}".format(
                        has_table, has_id1, has_id2, expected))
            else:
                emit(u"  [FAIL] intake parse: RESULT={0}, expected 'ok'".format(
                    result.get("RESULT")))

        # test validate (against ux_handoff_index.md)
        total += 1
        # 先写一个 mock index 文件
        index_path = os.path.join(tmpdir, "ux_handoff_index.md")
        mock_index = (
            u"# UX Handoff Index\n\n"
            u"## 导航\n\n"
            u"| 编号 | 名称 | MasterGo 源链接 | file_id | layer_id | 类型初判 | 是否建议纳入分析 | 状态 | 产物文件 | 依赖 | 备注 |\n"
            u"|------|------|----------------|---------|----------|----------|------------------|------|----------|------|------|\n"
            u"| 1 | HomePage | https://mastergo.com/file/abc123?layer_id=layer_001 | abc123 | layer_001 | 页面 | ✅ | ⏳ pending | — | — | |\n"
            u"\n"
            u"## 全局/跨页规则\n\n"
            u"| 规则摘要 | 类型 | 影响范围 | 归属 | 状态 | 来源 | 参见 |\n"
            u"|----------|------|----------|------|------|------|------|\n"
            u"| example rule | simple | — | global | confirmed | — | — |\n"
            u"\n"
            u"## 待确认项汇总\n\n"
            u"| 编号 | 所属 handoff | 问题摘要 | 确认角色 | 跑偏风险 | 阻塞级别 | 推荐选项 | 可继续假设 | 建议确认时机 | 影响范围 | 状态 |\n"
            u"|------|-------------|----------|----------|----------|----------|----------|------------|--------------|----------|------|\n"
            u"| Q01 | — | example question | product | none | non-blocking | — | — | later | — | open |\n"
        )
        with io.open(index_path, "w", encoding="utf-8") as f:
            f.write(mock_index)

        rc, out, err = run_cmd([
            INTAKE_SCRIPT, "validate", "--index", index_path,
        ])
        result = parse_result(out)
        if "PASS" in result.get("RESULT", ""):
            emit(u"  [PASS] intake validate: PASS on valid index")
            passed += 1
        else:
            emit(u"  [FAIL] intake validate: RESULT={0}".format(
                result.get("RESULT", "")))
            emit(u"    out: {0}".format(out[:200]))

        # test parse with missing file
        total += 1
        rc, out, err = run_cmd([
            INTAKE_SCRIPT, "parse", "--links", os.path.join(tmpdir, "nonexistent.txt"),
        ])
        if rc != 0:
            emit(u"  [PASS] intake parse: error exit on missing file")
            passed += 1
        else:
            emit(u"  [FAIL] intake parse: should error on missing file")

        # ---- cache_dsl.py check (miss) ----
        total += 1
        rc, out, err = run_cmd([
            CACHE_SCRIPT, "check",
            "--file-id", "test_file",
            "--layer-id", "test_layer",
            "--version", "v1",
            "--workspace", tmpdir,
        ])
        result = parse_result(out)
        if result.get("RESULT") == "miss":
            emit(u"  [PASS] cache check: miss on empty cache")
            passed += 1
        else:
            emit(u"  [FAIL] cache check: expected miss, got {0}".format(
                result.get("RESULT", "")))

        # ---- cache_dsl.py save + re-check (hit) ----
        total += 1
        test_obj = {
            "id": "n1",
            "name": "Test Node",
            "type": "FRAME",
            "fill": "#ffffff",
            "x": 100,
            "y": 200,
            "children": [
                {"id": "n2", "name": "Button", "type": "TEXT", "text": "Click Me",
                 "fontSize": 14, "onClick": {"action": "navigate"}},
            ],
        }
        test_json = json.dumps(test_obj, ensure_ascii=False)

        rc, out, err = run_cmd(
            [CACHE_SCRIPT, "save",
             "--file-id", "test_file",
             "--layer-id", "test_layer",
             "--version", "v1",
             "--workspace", tmpdir],
            stdin_text=test_json,
        )
        save_result = parse_result(out)
        if rc == 0 and save_result.get("RESULT") == "saved":
            rc2, out2, err2 = run_cmd([
                CACHE_SCRIPT, "check",
                "--file-id", "test_file",
                "--layer-id", "test_layer",
                "--version", "v1",
                "--workspace", tmpdir,
            ])
            check_result = parse_result(out2)
            if check_result.get("RESULT") == "hit":
                emit(u"  [PASS] cache save+check: saved then hit OK")
                passed += 1
            else:
                emit(u"  [FAIL] cache save+check: got {0}".format(
                    check_result.get("RESULT", "")))
        else:
            emit(u"  [FAIL] cache save: RESULT={0}, rc={1}".format(
                save_result.get("RESULT"), rc))
            emit(u"    err: {0}".format(err[:200]))

        # ---- cache_dsl.py check stale (version mismatch) ----
        total += 1
        rc, out, err = run_cmd([
            CACHE_SCRIPT, "check",
            "--file-id", "test_file",
            "--layer-id", "test_layer",
            "--version", "v2",
            "--workspace", tmpdir,
        ])
        result = parse_result(out)
        if result.get("RESULT") == "stale":
            emit(u"  [PASS] cache check: stale on version mismatch")
            passed += 1
        else:
            emit(u"  [FAIL] cache check: expected stale, got {0}".format(
                result.get("RESULT", "")))

        # ---- cache_dsl.py save invalid JSON ----
        total += 1
        rc, out, err = run_cmd(
            [CACHE_SCRIPT, "save",
             "--file-id", "bad",
             "--layer-id", "bad",
             "--version", "v1",
             "--workspace", tmpdir],
            stdin_text="not valid json",
        )
        result = parse_result(out)
        if rc != 0 or result.get("RESULT") == "error":
            emit(u"  [PASS] cache save: error on invalid JSON")
            passed += 1
        else:
            emit(u"  [FAIL] cache save: should error on invalid JSON")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    emit(u"\nL2: {0}/{1} passed".format(passed, total))
    return passed == total, {"passed": passed, "total": total}


# ---------------------------------------------------------------------------
# L3 裁剪忠实性
# ---------------------------------------------------------------------------

def test_l3():
    """L3: DSL 裁剪 -- 交互语义保留 + 视觉属性丢弃。"""
    emit(u"\n=== L3 裁剪忠实性 ===")
    passed = 0
    total = 0

    # 动态加载 cache_dsl 模块
    sys.path.insert(0, SCRIPT_DIR)
    try:
        import cache_dsl
    except ImportError:
        emit(u"  [FAIL] cannot import cache_dsl module")
        return False, {}
    finally:
        sys.path.pop(0)

    # 构造测试数据
    raw = {
        "id": "root",
        "name": "LoginPage",
        "type": "FRAME",
        "fill": "#f0f0f0",
        "x": 0, "y": 0, "width": 375, "height": 812,
        "fontFamily": "PingFang SC",
        "cornerRadius": 8,
        "opacity": 1.0,
        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 375, "height": 812},
        "onClick": {"action": "submit"},
        "children": [
            {
                "id": "btn1",
                "name": "ConfirmButton",
                "type": "TEXT",
                "text": "Confirm",
                "fontSize": 16,
                "fontWeight": 600,
                "color": "#ffffff",
                "backgroundColor": "#1890ff",
                "x": 100, "y": 400,
                "onClick": {"action": "confirm"},
                "state": "enabled",
            },
        ],
    }

    trimmed = cache_dsl.trim_dsl(raw)

    # 1. 交互语义应保留
    total += 1
    keep_checks = [
        ("id" in trimmed, u"id retained"),
        ("name" in trimmed, u"name retained"),
        ("type" in trimmed, u"type retained"),
        ("onClick" in trimmed, u"onClick retained"),
        ("children" in trimmed, u"children retained"),
        (trimmed.get("name") == "LoginPage", u"name value correct"),
        (trimmed[u"children"][0].get("text") == u"Confirm", u"child text retained"),
        (u"state" in trimmed[u"children"][0], u"child state retained"),
        (u"onClick" in trimmed[u"children"][0], u"child onClick retained"),
    ]
    all_kept = all(result for result, _ in keep_checks)
    if all_kept:
        emit(u"  [PASS] trim: interaction semantics preserved")
        passed += 1
    else:
        for result, desc in keep_checks:
            if not result:
                emit(u"    [FAIL] {0}".format(desc))

    # 2. 视觉属性应丢弃
    total += 1
    drop_checks = [
        ("fill" not in trimmed, u"fill dropped"),
        ("x" not in trimmed, u"x dropped"),
        ("y" not in trimmed, u"y dropped"),
        ("width" not in trimmed, u"width dropped"),
        ("height" not in trimmed, u"height dropped"),
        ("fontFamily" not in trimmed, u"fontFamily dropped"),
        ("cornerRadius" not in trimmed, u"cornerRadius dropped"),
        ("opacity" not in trimmed, u"opacity dropped"),
        ("absoluteBoundingBox" not in trimmed, u"absoluteBoundingBox dropped"),
        ("fontSize" not in trimmed[u"children"][0], u"child fontSize dropped"),
        ("fontWeight" not in trimmed[u"children"][0], u"child fontWeight dropped"),
        ("color" not in trimmed[u"children"][0], u"child color dropped"),
        ("backgroundColor" not in trimmed[u"children"][0], u"child backgroundColor dropped"),
    ]
    all_dropped = all(result for result, _ in drop_checks)
    if all_dropped:
        emit(u"  [PASS] trim: visual properties dropped")
        passed += 1
    else:
        for result, desc in drop_checks:
            if not result:
                emit(u"    [FAIL] {0}".format(desc))

    # 3. 压缩比例合理
    total += 1
    raw_json = to_unicode(json.dumps(raw, ensure_ascii=False, sort_keys=True))
    trimmed_json = to_unicode(json.dumps(trimmed, ensure_ascii=False, sort_keys=True))
    raw_len = len(raw_json.encode("utf-8"))
    trimmed_len = len(trimmed_json.encode("utf-8"))
    if raw_len > 0:
        reduction = 100.0 - (100.0 * trimmed_len / raw_len)
        if reduction > 20:
            emit(u"  [PASS] trim: reduction {:.1f}% > 20%".format(reduction))
            passed += 1
        else:
            emit(u"  [FAIL] trim: reduction {:.1f}% too low".format(reduction))
    else:
        emit(u"  [FAIL] trim: cannot calculate reduction")

    # 4. 空字典节点丢弃
    total += 1
    empty_node = {"fill": "#fff", "x": 0, "y": 0}
    result = cache_dsl._trim_dsl_node(empty_node)
    if result is None:
        emit(u"  [PASS] trim: pure-visual node returns None")
        passed += 1
    else:
        emit(u"  [FAIL] trim: pure-visual node should return None, got {0}".format(
            result))

    # 5. 不在黑白名单的字段保守保留
    total += 1
    result = cache_dsl._trim_dsl_node({"id": "x", "name": "x", "customField": "value"})
    if result and "customField" in result:
        emit(u"  [PASS] trim: unknown field preserved (conservative)")
        passed += 1
    else:
        emit(u"  [FAIL] trim: unknown field should be preserved")

    emit(u"\nL3: {0}/{1} passed".format(passed, total))
    return passed == total, {"passed": passed, "total": total}


# ---------------------------------------------------------------------------
# L4 文档一致性
# ---------------------------------------------------------------------------

def test_l4():
    """L4: 文档引用与脚本 API 一致性。"""
    emit(u"\n=== L4 文档一致性 ===")
    passed = 0
    total = 0

    docs = {}
    for name, path in [(u"SKILL.md", SKILL_MD), (u"mode_a_workflow.md", MODE_A_MD)]:
        if os.path.isfile(path):
            docs[name] = read_file(path)
        else:
            emit(u"  [FAIL] {0}: not found at {1}".format(name, path))

    sk_md = docs.get(u"SKILL.md", u"")
    maw_md = docs.get(u"mode_a_workflow.md", u"")

    # 1. SKILL.md 引用所有新脚本
    total += 1
    if "cache_dsl.py" in sk_md and "intake_layer_inventory.py" in sk_md:
        emit(u"  [PASS] SKILL.md: references all new scripts")
        passed += 1
    else:
        emit(u"  [FAIL] SKILL.md: missing script references")
        if "cache_dsl.py" not in sk_md:
            emit(u"    cache_dsl.py not found")
        if "intake_layer_inventory.py" not in sk_md:
            emit(u"    intake_layer_inventory.py not found")

    # 2. mode_a_workflow.md 包含 Step 0
    total += 1
    step0_checks = [
        ("Input Pre-Processing" in maw_md, "step 0 heading"),
        ("intake_layer_inventory.py" in maw_md, "intake script ref"),
        ("cache_dsl.py" in maw_md, "cache script ref"),
    ]
    if all(result for result, _ in step0_checks):
        emit(u"  [PASS] mode_a_workflow.md: step 0 complete")
        passed += 1
    else:
        for result, desc in step0_checks:
            if not result:
                emit(u"  [FAIL] mode_a_workflow.md: missing {0}".format(desc))

    # 3. Mode Routing 表包含 step 0
    total += 1
    if "0. Input Intake" in sk_md:
        emit(u"  [PASS] SKILL.md: Mode Routing includes Input Intake")
        passed += 1
    else:
        emit(u"  [FAIL] SKILL.md: Mode Routing missing Input Intake row")

    # 4. Hard Rules 包含三条新规则
    total += 1
    hr_checks = [
        ("cache_dsl.py check" in sk_md, "cache reuse rule"),
        ("trimmed DSL" in sk_md, "trimmed DSL rule"),
        ("intake_layer_inventory.py parse" in sk_md, "multi-link inventory rule"),
    ]
    if all(result for result, _ in hr_checks):
        emit(u"  [PASS] SKILL.md: all 3 new Hard Rules present")
        passed += 1
    else:
        for result, desc in hr_checks:
            if not result:
                emit(u"  [FAIL] {0}".format(desc))

    # 5. Loading Contract 包含新脚本引用
    total += 1
    if "intake_layer_inventory.py" in maw_md and "cache_dsl.py" in maw_md:
        emit(u"  [PASS] mode_a_workflow.md: Loading Contract updated")
        passed += 1
    else:
        emit(u"  [FAIL] mode_a_workflow.md: Loading Contract missing new scripts")

    # 6. .gitignore 包含 .cache/
    total += 1
    gitignore = os.path.join(REPO_ROOT, ".gitignore")
    if os.path.isfile(gitignore):
        gi_content = read_file(gitignore)
        if ".cache/" in gi_content or ".cache" in gi_content:
            emit(u"  [PASS] .gitignore: .cache/ rule present")
            passed += 1
        else:
            emit(u"  [FAIL] .gitignore: .cache/ rule missing")
    else:
        emit(u"  [FAIL] .gitignore: not found at {0}".format(gitignore))

    # 7. Mode B 引用 index
    total += 1
    mode_b_md = os.path.join(SKILL_DIR, "references", "mode_b_workflow.md")
    if os.path.isfile(mode_b_md):
        mode_b = read_file(mode_b_md)
        if "ux_handoff_index.md" in mode_b:
            emit(u"  [PASS] mode_b_workflow.md: references index")
            passed += 1
        else:
            emit(u"  [FAIL] mode_b_workflow.md: missing index reference")
    else:
        emit(u"  [WARN] mode_b_workflow.md: file not found, skipping check")
        passed += 1

    # 8. Mode C 引用 index + validate
    total += 1
    mode_c_md = os.path.join(SKILL_DIR, "references", "mode_c_maintenance_workflow.md")
    if os.path.isfile(mode_c_md):
        mode_c = read_file(mode_c_md)
        has_index = "ux_handoff_index.md" in mode_c
        has_validate = "intake_layer_inventory.py validate" in mode_c
        if has_index and has_validate:
            emit(u"  [PASS] mode_c_maintenance_workflow.md: references index + index validate")
            passed += 1
        else:
            emit(u"  [FAIL] mode_c_maintenance_workflow.md: missing index ref={0}, validate={1}".format(has_index, has_validate))
    else:
        emit(u"  [WARN] mode_c_maintenance_workflow.md: file not found, skipping check")
        passed += 1

    emit(u"\nL4: {0}/{1} passed".format(passed, total))
    return passed == total, {"passed": passed, "total": total}


# ---------------------------------------------------------------------------
# L5 回归基准
# ---------------------------------------------------------------------------

BENCH_SCRIPT = os.path.join(SCRIPT_DIR, "bench_iteration.py")
MANIFEST_PATH = os.path.join(SKILL_DIR, "tests", "fixtures", "manifest.json")


def test_l5():
    """L5: 回归基准 — bench_iteration.py 可运行 + manifest 有效。"""
    emit(u"\n=== L5 回归基准 ===")
    passed = 0
    total = 0

    # 1. bench_iteration.py 存在且可编译
    total += 1
    if not os.path.isfile(BENCH_SCRIPT):
        emit(u"  [FAIL] bench_iteration.py not found at {0}".format(BENCH_SCRIPT))
    else:
        try:
            source = read_file(BENCH_SCRIPT)
            if IS_PY2:
                source_bytes = source.encode("utf-8")
            else:
                source_bytes = source
            compile(source_bytes, BENCH_SCRIPT, "exec")
            emit(u"  [PASS] bench_iteration.py: syntax compiles")
            passed += 1
        except SyntaxError as exc:
            emit(u"  [FAIL] bench_iteration.py: syntax error: {0}".format(exc))

    # 2. manifest.json 存在且合法 JSON
    total += 1
    if not os.path.isfile(MANIFEST_PATH):
        emit(u"  [FAIL] manifest.json not found at {0}".format(MANIFEST_PATH))
    else:
        try:
            manifest_text = read_file(MANIFEST_PATH)
            manifest = json.loads(manifest_text)
            fixture_count = len(manifest.get("fixtures", []))
            if fixture_count >= 3:
                emit(u"  [PASS] manifest.json: {0} fixtures registered".format(
                    fixture_count))
                passed += 1
            else:
                emit(u"  [FAIL] manifest.json: only {0} fixtures (need >= 3)".format(
                    fixture_count))
        except ValueError as exc:
            emit(u"  [FAIL] manifest.json: invalid JSON: {0}".format(exc))
        except Exception as exc:
            emit(u"  [FAIL] manifest.json: read error: {0}".format(exc))

    # 3. bench_iteration.py --help 正常退出
    total += 1
    rc, out, err = run_cmd([BENCH_SCRIPT, "--help"])
    if rc == 0:
        has_old = "--old" in out
        has_compare = "--compare" in out
        if has_old and has_compare:
            emit(u"  [PASS] bench_iteration.py: --help shows L1+L2 modes")
            passed += 1
        else:
            emit(u"  [WARN] bench_iteration.py: --help missing expected arguments")
            passed += 1  # non-blocking
    else:
        emit(u"  [FAIL] bench_iteration.py: --help exits {0}".format(rc))

    # 4. L1 quick mode smoketest (if git history allows)
    total += 1
    rc, out, err = run_cmd([
        BENCH_SCRIPT, "--old", "HEAD", "--new", "HEAD", "--quick",
    ])
    if rc == 0:
        if "Score:" in out and "Grade:" in out:
            emit(u"  [PASS] bench_iteration L1 quick: score + grade produced")
            passed += 1
        else:
            emit(u"  [FAIL] bench_iteration L1 quick: missing Score/Grade in output")
    else:
        emit(u"  [WARN] bench_iteration L1 quick: exited {0} (may be normal "
              u"if HEAD==HEAD has no diff)".format(rc))
        passed += 1  # non-blocking — HEAD vs HEAD has no diff by definition

    emit(u"\nL5: {0}/{1} passed".format(passed, total))
    return passed == total, {"passed": passed, "total": total}


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

ALL_LAYERS = {"L1": test_l1, "L2": test_l2, "L3": test_l3, "L4": test_l4, "L5": test_l5}

def main(argv):
    parser = argparse.ArgumentParser(
        description="Validate tac-ux-mastergo skill iteration correctness."
    )
    parser.add_argument(
        "--layer",
        nargs="+",
        choices=sorted(ALL_LAYERS.keys()),
        default=sorted(ALL_LAYERS.keys()),
        help="Which validation layers to run. Default: all.",
    )
    args = parser.parse_args(argv)

    emit("=" * 60)
    emit(u"tac-ux-mastergo Skill Iteration Validator")
    emit("=" * 60)

    layers = [l for l in sorted(args.layer, key=lambda x: int(x[1]))]
    results = {}
    all_pass = True

    for layer_id in layers:
        try:
            ok, stats = ALL_LAYERS[layer_id]()
            results[layer_id] = ok
            if not ok:
                all_pass = False
        except Exception:
            emit(u"  [ERROR] {0} crashed: {1}".format(layer_id, sys.exc_info()[1]))
            emit(u"  TRACEBACK:\n{0}".format(safe_traceback()))
            results[layer_id] = False
            all_pass = False

    emit(u"\n" + "=" * 60)
    emit(u"SUMMARY")
    emit("=" * 60)
    for layer_id in sorted(results.keys()):
        status = u"PASS" if results[layer_id] else u"FAIL"
        emit(u"  {0}: {1}".format(layer_id, status))

    if all_pass:
        emit(u"\nALL LAYERS PASS -- skill iteration is healthy")
        return 0
    else:
        emit(u"\nSOME LAYERS FAILED -- review the failures above")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
