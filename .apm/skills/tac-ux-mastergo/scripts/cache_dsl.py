#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""cache_dsl.py -- 管理 MasterGo DSL 本地缓存与交互语义裁剪。

提供两个子命令：
  check  -- 检查缓存是否有效（判重）
  save   -- 从 stdin 写入 raw DSL，同步生成 trimmed + meta

缓存目录结构：
  {cache_dir}/{file_id}/
    {layer_id}_raw.json      # 原始全量 DSL
    {layer_id}_trimmed.json  # 裁剪后交互语义 DSL
    {layer_id}_meta.json     # 缓存元信息

Python 3.6+ required.
"""

import argparse
import hashlib
import json
import os
import sys
import time


# ---------------------------------------------------------------------------
# DSL 交互语义裁剪
# ---------------------------------------------------------------------------

# 保留字段白名单 -- 交互分析需要的数据
_KEEP_FIELDS = frozenset([
    "id",
    "name",
    "type",
    "children",
    "text",
    "description",
    "visible",
    "interactions",
    "onClick",
    "onHover",
    "onPress",
    "onFocus",
    "onBlur",
    "state",
    "variant",
    "annotations",
    "componentProperties",
    "componentId",
    "instanceId",
    "layerId",
    "fileId",
])

# 裁剪字段黑名单 -- 纯视觉还原属性
_DROP_FIELDS = frozenset([
    # 颜色
    "fill",
    "fillGeometry",
    "stroke",
    "strokeWeight",
    "strokeAlign",
    "strokeCap",
    "strokeJoin",
    "background",
    "backgroundColor",
    "backgrounds",
    "gradient",
    "color",
    "fills",
    "strokes",
    # 布局坐标
    "x",
    "y",
    "width",
    "height",
    "absoluteBoundingBox",
    "absoluteRenderBounds",
    "relativeTransform",
    # 字体
    "fontFamily",
    "fontName",
    "fontSize",
    "fontWeight",
    "fontPostScriptName",
    "lineHeight",
    "letterSpacing",
    "textAlignHorizontal",
    "textAlignVertical",
    "textAutoResize",
    "textCase",
    "textDecoration",
    # 样式
    "opacity",
    "cornerRadius",
    "rectangleCornerRadii",
    "cornerSmoothing",
    "blendMode",
    "effects",
    "effectStyleId",
    "shadow",
    "innerShadow",
    "dropShadow",
    # 布局约束
    "constraints",
    "constrainProportions",
    "layoutMode",
    "layoutAlign",
    "layoutGrow",
    "layoutPositioning",
    "layoutSizingHorizontal",
    "layoutSizingVertical",
    "itemSpacing",
    "counterAxisSpacing",
    "counterAxisAlignContent",
    "counterAxisAlignItems",
    "primaryAxisAlignItems",
    "primaryAxisSizingMode",
    "counterAxisSizingMode",
    "paddingLeft",
    "paddingRight",
    "paddingTop",
    "paddingBottom",
    "padding",
    "margin",
    "itemReverseZIndex",
    "strokesIncludedInLayout",
    # 资源和导出
    "exportSettings",
    "imageUrl",
    "imageHash",
    "fillOverrideTable",
    "styleType",
    "styleId",
    "assetKey",
    # 画布/视口
    "clipsContent",
    "isMask",
    "maskType",
    "frameMaskDisabled",
    "canvasSize",
    "viewport",
    # 其他视觉相关
    "strokeStyleId",
    "fillStyleId",
    "individualStrokeWeights",
    "dashPattern",
    "strokeMiterAngle",
    "strokeTopWeight",
    "strokeBottomWeight",
    "strokeLeftWeight",
    "strokeRightWeight",
])


def _trim_dsl_node(node):
    """递归裁剪单个 DSL node，只保留交互语义字段。

    返回值：
      裁剪后的节点 dict，或 None（如果节点完全没有保留字段）
    保守策略：不在白名单也不在黑名单的字段保留。
    """
    if not isinstance(node, dict):
        return node

    trimmed = {}
    for key, value in node.items():
        if key in _DROP_FIELDS:
            continue
        if key == "children" and isinstance(value, list):
            kept_children = []
            for child in value:
                trimmed_child = _trim_dsl_node(child)
                if trimmed_child is not None:
                    kept_children.append(trimmed_child)
            trimmed["children"] = kept_children
        elif isinstance(value, dict):
            sub = _trim_dsl_node(value)
            if sub is not None:
                trimmed[key] = sub
        elif isinstance(value, list):
            # 对列表中的每个元素（如果不是 children）也尝试递归
            kept_items = []
            for item in value:
                if isinstance(item, dict):
                    sub = _trim_dsl_node(item)
                    if sub is not None:
                        kept_items.append(sub)
                else:
                    kept_items.append(item)
            trimmed[key] = kept_items
        else:
            trimmed[key] = value

    # 完全空节点丢弃
    if not trimmed:
        return None
    return trimmed


def trim_dsl(raw_data):
    """对完整的 raw DSL JSON 执行交互语义裁剪。

    参数：
      raw_data: dict，从 MCP getDsl 获取的原始 DSL

    返回：
      dict，裁剪后的交互语义 DSL
    """
    if isinstance(raw_data, dict):
        result = _trim_dsl_node(raw_data)
        return result if result is not None else {}
    return raw_data


# ---------------------------------------------------------------------------
# 缓存工具函数
# ---------------------------------------------------------------------------

def _cache_dir_for(workspace_dir, file_id):
    """返回指定 file_id 的缓存目录路径。"""
    return os.path.join(workspace_dir, ".cache", "tac-ux-mastergo", file_id)


def _safe_layer_id(layer_id):
    """将 layer_id 中的非法文件名字符替换为下划线。

    MasterGo layer_id 格式为 "file_id:node_id"（如 "1565:16701"），
    其中的 ":" 在 Windows 上触发 NTFS Alternate Data Stream 行为，
    导致文件无法按预期读写。统一替换为 "_" 避免跨平台问题。
    """
    return layer_id.replace(":", "_").replace("/", "_").replace("\\", "_")


def _meta_path(cache_dir, layer_id):
    return os.path.join(cache_dir, "{0}_meta.json".format(_safe_layer_id(layer_id)))


def _raw_path(cache_dir, layer_id):
    return os.path.join(cache_dir, "{0}_raw.json".format(_safe_layer_id(layer_id)))


def _trimmed_path(cache_dir, layer_id):
    return os.path.join(cache_dir, "{0}_trimmed.json".format(_safe_layer_id(layer_id)))


def _read_json(path):
    with open(path, "rb") as handle:
        return json.load(handle)


def _write_json(path, data):
    """原子写入 JSON 文件并执行写后验证。

    先写入临时文件，flush + fsync 确保落盘后再进行 JSON 解析校验，
    校验通过后通过原子 rename 替换目标文件，防止写入中断导致缓存损坏。
    """
    dirname = os.path.dirname(path)
    if dirname and not os.path.isdir(dirname):
        os.makedirs(dirname)

    json_str = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
    encoded = json_str.encode("utf-8")

    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        if os.path.isfile(tmp_path):
            os.remove(tmp_path)
        raise

    # 写后验证：重新读取并解析，确保 JSON 完整性
    try:
        with open(tmp_path, "rb") as handle:
            json.load(handle)
    except (ValueError, IOError) as exc:
        if os.path.isfile(tmp_path):
            os.remove(tmp_path)
        raise IOError("Post-write validation failed for {0}: {1}".format(path, exc))

    # 原子替换（Windows 上 rename 不会覆盖已有文件，需先删除）
    if sys.platform == "win32" and os.path.isfile(path):
        os.remove(path)
    os.rename(tmp_path, path)


def _raw_size(raw_data):
    """估算 raw JSON 的字节大小。"""
    return len(json.dumps(raw_data, ensure_ascii=False, sort_keys=True))


def _trimmed_size(trimmed_data):
    """估算 trimmed JSON 的字节大小。"""
    return len(json.dumps(trimmed_data, ensure_ascii=False, sort_keys=True))


def _sha256_hex(data):
    """数据 dict 序列化后的 SHA-256 hex 字串。"""
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------------------
# emit -- Python 3 Unicode 安全输出
# ---------------------------------------------------------------------------

def emit(text):
    """Python 3 + Windows GBK 终端的 Unicode 安全输出。"""
    try:
        print(text)
    except UnicodeEncodeError:
        if hasattr(sys.stdout, "buffer"):
            sys.stdout.buffer.write(text.encode("utf-8", errors="replace") + b"\n")
        else:
            print(text.encode("ascii", errors="replace").decode("ascii"))


# ---------------------------------------------------------------------------
# 子命令：check
# ---------------------------------------------------------------------------

def cmd_check(args):
    """检查指定 layer 的缓存有效性。"""
    cache_dir = _cache_dir_for(args.workspace, args.file_id)
    meta_file = _meta_path(cache_dir, args.layer_id)
    trimmed_file = _trimmed_path(cache_dir, args.layer_id)

    if not os.path.isfile(meta_file):
        emit("RESULT: miss")
        emit("TRIM_PATH: (null)")
        return 0

    try:
        meta = _read_json(meta_file)
    except (ValueError, IOError):
        emit("RESULT: miss")
        emit("REASON: meta corrupted")
        emit("TRIM_PATH: (null)")
        return 0

    cached_version = meta.get("version", "")
    if str(cached_version) != str(args.version):
        emit("RESULT: stale")
        emit("CACHED_VERSION: {0}".format(cached_version))
        emit("REQUESTED_VERSION: {0}".format(args.version))
        emit("CACHED_AT: {0}".format(meta.get("fetched_at", "unknown")))
        emit("TRIM_PATH: (null)")
        return 0

    if not os.path.isfile(trimmed_file):
        emit("RESULT: stale")
        emit("REASON: trimmed file missing")
        emit("TRIM_PATH: (null)")
        return 0

    # 验证 trimmed 文件 JSON 完整性，防止使用损坏的缓存
    try:
        _read_json(trimmed_file)
    except (ValueError, IOError):
        emit("RESULT: stale")
        emit("REASON: trimmed file corrupted (invalid JSON)")
        emit("TRIM_PATH: (null)")
        return 0

    emit("RESULT: hit")
    emit("TRIM_PATH: {0}".format(trimmed_file))
    emit("RAW_SIZE: {0}".format(meta.get("raw_size_bytes", "unknown")))
    emit("TRIMMED_SIZE: {0}".format(meta.get("trimmed_size_bytes", "unknown")))
    emit("FETCHED_AT: {0}".format(meta.get("fetched_at", "unknown")))
    return 0


# ---------------------------------------------------------------------------
# 子命令：save
# ---------------------------------------------------------------------------

def _validate_dsl_completeness(data):
    """Validate DSL data structural completeness. Returns (ok: bool, reason: str)."""
    dsl = data.get("dsl", data)
    nodes = dsl.get("nodes", [])
    if not nodes:
        return (False, "DSL has no nodes — possibly empty or truncated.")
    root = nodes[0] if nodes else None
    if root and root.get("type") == "FRAME":
        children = root.get("children", [])
        if not children:
            return (False, "Root FRAME node has no children — possibly truncated.")
        return (True, "complete ({0} children)".format(len(children)))
    return (True, "complete ({0} nodes)".format(len(nodes)))


def cmd_save(args):
    """从 stdin 或 --input-file 读取 raw DSL，裁剪后写入缓存。

    当 --validate-first 启用时，先做结构性完整性校验，
    截断/可疑数据拒绝写入并返回错误码。
    """
    if args.input_file:
        with open(args.input_file, "rb") as handle:
            raw_text = handle.read().decode("utf-8")
    else:
        raw_text = sys.stdin.read()

    try:
        raw_data = json.loads(raw_text)
    except ValueError as exc:
        emit("RESULT: error")
        emit("REASON: invalid JSON input: {0}".format(exc))
        return 1

    # --validate-first: 写入前先做截断检测
    if args.validate_first:
        ok, reason = _validate_dsl_completeness(raw_data)
        if not ok:
            emit("RESULT: truncated")
            emit("REASON: {0}".format(reason))
            emit("ACTION: Re-fetch DSL with a larger maxOutputLength (suggest: double current value).")
            return 1

    trimmed_data = trim_dsl(raw_data)

    cache_dir = _cache_dir_for(args.workspace, args.file_id)
    raw_file = _raw_path(cache_dir, args.layer_id)
    trimmed_file = _trimmed_path(cache_dir, args.layer_id)
    meta_file = _meta_path(cache_dir, args.layer_id)

    now = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())

    try:
        _write_json(raw_file, raw_data)
        _write_json(trimmed_file, trimmed_data)
    except (ValueError, IOError, IOError) as exc:
        emit("RESULT: error")
        emit("REASON: write failed: {0}".format(exc))
        return 1

    meta = {
        "file_id": args.file_id,
        "layer_id": args.layer_id,
        "version": str(args.version),
        "fetched_at": now,
        "raw_hash": _sha256_hex(raw_data),
        "raw_size_bytes": _raw_size(raw_data),
        "trimmed_size_bytes": _trimmed_size(trimmed_data),
    }
    try:
        _write_json(meta_file, meta)
    except (ValueError, IOError, IOError) as exc:
        emit("RESULT: error")
        emit("REASON: meta write failed: {0}".format(exc))
        return 1

    # 计算压缩比例
    raw_sz = meta["raw_size_bytes"]
    trimmed_sz = meta["trimmed_size_bytes"]
    if raw_sz > 0:
        reduction_pct = 100.0 - (100.0 * trimmed_sz / raw_sz)
    else:
        reduction_pct = 0.0

    emit("RESULT: saved")
    emit("RAW_PATH: {0}".format(raw_file))
    emit("TRIMMED_PATH: {0}".format(trimmed_file))
    emit("META_PATH: {0}".format(meta_file))
    emit("RAW_SIZE: {0}".format(raw_sz))
    emit("TRIMMED_SIZE: {0}".format(trimmed_sz))
    emit("REDUCTION: {0:.1f}%".format(reduction_pct))
    return 0


# ---------------------------------------------------------------------------
# 子命令：validate-truncation
# ---------------------------------------------------------------------------

def cmd_validate_truncation(args):
    """检测 DSL JSON 是否被截断。"""
    if args.input_file:
        with open(args.input_file, "rb") as handle:
            raw_text = handle.read().decode("utf-8")
    else:
        raw_text = sys.stdin.read()

    # 1. JSON 解析 — 截断的 JSON 会在这里失败
    try:
        data = json.loads(raw_text)
    except ValueError as exc:
        emit("RESULT: truncated")
        emit("REASON: JSON parse failed — data is incomplete: {0}".format(exc))
        emit("ACTION: Re-fetch DSL with a larger maxOutputLength (suggest: double current value).")
        return 1

    # 2. 结构性完整性检查（复用公共校验函数）
    ok, reason = _validate_dsl_completeness(data)
    if not ok:
        emit("RESULT: suspicious")
        emit("REASON: {0}".format(reason))
        emit("ACTION: Re-fetch with larger maxOutputLength.")
        return 1

    # 3. 输出详情
    dsl = data.get("dsl", data)
    nodes = dsl.get("nodes", [])
    root = nodes[0] if nodes else None
    if root and root.get("type") == "FRAME":
        children = root.get("children", [])
        emit("RESULT: complete")
        emit("ROOT_TYPE: {0}".format(root.get("type", "unknown")))
        emit("ROOT_NAME: {0}".format(root.get("name", "unknown")))
        emit("CHILD_COUNT: {0}".format(len(children)))
    else:
        emit("RESULT: complete")
        emit("NODES_COUNT: {0}".format(len(nodes)))

    return 0


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main(argv):
    parser = argparse.ArgumentParser(
        description="Manage MasterGo DSL cache with interaction-semantic trimming."
    )
    subparsers = parser.add_subparsers(dest="command")

    # ---- check ----
    check_parser = subparsers.add_parser("check", help="Check if cached DSL is still valid.")
    check_parser.add_argument("--file-id", required=True, help="MasterGo file ID.")
    check_parser.add_argument("--layer-id", required=True, help="MasterGo layer ID.")
    check_parser.add_argument("--version", required=True, help="Expected DSL version (from MCP getMeta).")
    check_parser.add_argument(
        "--workspace",
        default=os.getcwd(),
        help="Workspace root for .cache/ directory. Default: current directory.",
    )
    check_parser.set_defaults(func=cmd_check)

    # ---- save ----
    save_parser = subparsers.add_parser("save", help="Save raw DSL from stdin or file and write trimmed version.")
    save_parser.add_argument("--file-id", required=True, help="MasterGo file ID.")
    save_parser.add_argument("--layer-id", required=True, help="MasterGo layer ID.")
    save_parser.add_argument("--version", required=True, help="DSL version identifier.")
    save_parser.add_argument(
        "--input-file",
        default=None,
        help="Read raw DSL from file instead of stdin. Useful when piping large JSON is impractical.",
    )
    save_parser.add_argument(
        "--validate-first",
        action="store_true",
        default=False,
        help="Run truncation validation before saving. Refuses to write if DSL is incomplete.",
    )
    save_parser.add_argument(
        "--workspace",
        default=os.getcwd(),
        help="Workspace root for .cache/ directory. Default: current directory.",
    )
    save_parser.set_defaults(func=cmd_save)

    # ---- validate-truncation ----
    vt_parser = subparsers.add_parser(
        "validate-truncation",
        help="Check whether a raw DSL JSON file is complete (not truncated by MCP output limits).",
    )
    vt_parser.add_argument(
        "--input-file",
        default=None,
        help="Path to raw DSL JSON file. Reads from stdin if omitted.",
    )
    vt_parser.set_defaults(func=cmd_validate_truncation)

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
