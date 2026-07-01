"""
MasterGo Asset Extraction Pipeline v2 (Three-Step Architecture)

Manifest-driven icon extraction with concurrent component fetching support.

Subcommands:
    extract  - Download bitmaps + generate VectorDrawable XMLs + output missing list
    replace  - Replace @drawable/ph_icon_xxx placeholders in XML layouts with real names

Usage:
    python extract_assets.py extract <output_dir> <input1.json> [input2.json ...] --manifest <manifest.json>
    python extract_assets.py replace <layout_dir> <manifest.json>

Key changes from v1:
    - Icon detection is driven by placeholder_manifest.json, not width<=64 heuristic
    - Missing components output to structured JSON (not just log warnings)
    - 'replace' subcommand for post-extraction placeholder substitution
"""

import json
import logging
import os
import re
import sys
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)


def _sanitize_filename(name: str) -> str:
    """Convert a MasterGo node name to a safe Android resource filename."""
    safe = re.sub(r"[^a-zA-Z0-9_\-]", "_", name)
    safe = re.sub(r"_+", "_", safe).strip("_").lower()
    return safe or "asset"


def _canonical_icon_name(name: str) -> str:
    """Normalize icon names to the drawable resource name used in XML references.

    MasterGo icon instances often include a category prefix in `name`, e.g.
    `All/ic_all_account` or `Edit/ic_all_delete`. The drawable resource that
    should be referenced is the icon token itself (`ic_all_account`,
    `ic_all_delete`), not the category-prefixed sanitized form.
    """
    safe = _sanitize_filename(name)
    ic_index = safe.find("ic_")
    if ic_index > 0:
        return safe[ic_index:]
    return safe


def _is_shared_library_icon(name: str) -> bool:
    """Return True when the icon should default to a shared widget-library drawable."""
    return _canonical_icon_name(name).startswith("ic_")


def _color_to_android_hex(color_str: str) -> str:
    """Convert CSS color strings to Android XML hex #AARRGGBB or #RRGGBB."""
    color_str = color_str.strip()
    if color_str.startswith('#'):
        if len(color_str) == 4:  # #FFF
            return "#" + color_str[1] * 2 + color_str[2] * 2 + color_str[3] * 2
        return color_str.upper()
    elif color_str.startswith('rgba('):
        try:
            parts = color_str[5:-1].split(',')
            r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
            a = float(parts[3])
            a_int = int(a * 255)
            if a_int == 255:
                return f"#{r:02x}{g:02x}{b:02x}".upper()
            return f"#{a_int:02x}{r:02x}{g:02x}{b:02x}".upper()
        except Exception:
            return "#FF000000"
    elif color_str == 'currentColor':
        return "#FF000000"
    elif color_str == 'white':
        return "#FFFFFFFF"
    elif color_str == 'black':
        return "#FF000000"
    return "#FF000000"


def generate_vector_drawable(node: dict, xml_path: str) -> bool:
    """Generate Android VectorDrawable XML from a MasterGo Vector Node.
    
    Returns True if at least one path with data was rendered.
    """
    vw = float(node.get("layoutStyle", {}).get("width", 24) or 24)
    vh = float(node.get("layoutStyle", {}).get("height", 24) or 24)

    xml_lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<vector xmlns:android="http://schemas.android.com/apk/res/android"',
        f'    android:width="{vw:g}dp"',
        f'    android:height="{vh:g}dp"',
        f'    android:viewportWidth="{vw:g}"',
        f'    android:viewportHeight="{vh:g}">',
    ]

    has_path_data = False

    def traverse(n, parent_x=0.0, parent_y=0.0):
        nonlocal has_path_data
        ls = n.get("layoutStyle", {})
        rx = float(ls.get("relativeX", 0)) + parent_x
        ry = float(ls.get("relativeY", 0)) + parent_y

        if n.get("type") == "PATH":
            paths = n.get("path", [])
            if paths:
                has_translation = rx != 0 or ry != 0
                if has_translation:
                    xml_lines.append(
                        f'    <group android:translateX="{rx:g}" android:translateY="{ry:g}">'
                    )

                for p in paths:
                    data = p.get("data", "")
                    fill = p.get("fill", "#000000")
                    hex_fill = _color_to_android_hex(fill)

                    if data:
                        has_path_data = True
                        xml_lines.append("        <path")
                        xml_lines.append(f'            android:fillColor="{hex_fill}"')
                        xml_lines.append(f'            android:pathData="{data}" />')

                if has_translation:
                    xml_lines.append("    </group>")

        for c in n.get("children", []):
            traverse(c, rx, ry)

    traverse(node)
    xml_lines.append("</vector>")

    if has_path_data:
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write("\n".join(xml_lines) + "\n")
        return True
    return False


# ---------------------------------------------------------------------------
# Subcommand: extract
# ---------------------------------------------------------------------------

def cmd_extract(args):
    """Extract bitmaps and vector icons from DSL JSON files.
    
    Uses placeholder_manifest.json to precisely identify which nodes are icons,
    rather than relying on width<=64 heuristic.
    """
    if len(args) < 2:
        print("Usage: python extract_assets.py extract <output_dir> <input1.json> [input2.json ...] [--manifest <manifest.json>]")
        sys.exit(1)

    out_dir = Path(args[0])
    out_dir.mkdir(parents=True, exist_ok=True)

    # Parse --manifest flag
    manifest_path = None
    json_files = []
    i = 1
    while i < len(args):
        if args[i] == "--manifest" and i + 1 < len(args):
            manifest_path = args[i + 1]
            i += 2
        else:
            json_files.append(args[i])
            i += 1

    # Load manifest if provided
    manifest_icon_ids = set()
    if manifest_path and os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        for icon in manifest.get("icon_placeholders", []):
            cid = icon.get("component_id")
            if cid:
                manifest_icon_ids.add(cid)
        logger.info("Loaded manifest with %d icon component IDs", len(manifest_icon_ids))

    # Load all JSONs
    all_styles = {}
    all_nodes = []

    for js_file in json_files:
        with open(js_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            dsl_block = data.get("dsl", data)
            if "styles" in dsl_block:
                all_styles.update(dsl_block["styles"])
            if "nodes" in dsl_block:
                all_nodes.extend(dsl_block["nodes"])

    # Extract CDN image URLs from paint styles
    paint_urls = {}
    for k, v in all_styles.items():
        if isinstance(v, dict) and "value" in v:
            for val in v["value"]:
                if isinstance(val, dict) and "url" in val:
                    paint_urls[k] = val["url"]

    # Scan nodes
    raster_assets = []
    icon_assets = []
    missing_components = []
    shared_library_icons = set()
    global_components = {n.get("id"): n for n in all_nodes if n.get("type") == "COMPONENT"}

    def scan(n):
        typ = n.get("type", "")
        name = n.get("name", "asset")
        safe_name = _sanitize_filename(name)
        icon_name = _canonical_icon_name(name)

        # Raster image detection: node fill references a paint style with CDN URL
        fill = n.get("fill")
        if fill in paint_urls:
            raster_assets.append({
                "name": safe_name,
                "url": paint_urls[fill],
            })

        # Icon detection: manifest-driven (precise) or name-pattern fallback
        is_manifest_icon = False
        if typ == "INSTANCE":
            cid = n.get("componentId")
            if cid and (cid in manifest_icon_ids or _is_icon_by_name(name)):
                if _is_shared_library_icon(name):
                    shared_library_icons.add(icon_name)
                    return
                is_manifest_icon = True
                if cid in global_components:
                    icon_assets.append({"name": icon_name, "node": global_components[cid]})
                else:
                    missing_components.append({"name": icon_name, "component_id": cid})
                return  # Don't scan children of icon instances

        if typ == "COMPONENT":
            cid = n.get("id")
            if cid and (cid in manifest_icon_ids or _is_icon_by_name(name)):
                if _is_shared_library_icon(name):
                    shared_library_icons.add(icon_name)
                    return
                icon_assets.append({"name": icon_name, "node": n})

        for c in n.get("children", []):
            scan(c)

    for rn in all_nodes:
        scan(rn)

    # Deduplicate raster assets by name
    raster_map = {a["name"]: a["url"] for a in raster_assets}

    # --- Download Raster Images ---
    raster_dir = out_dir

    logger.info("Targeting %d raster images from CDN...", len(raster_map))
    download_count = 0
    for name, url in raster_map.items():
        dest = raster_dir / f"{name}.png"
        if not dest.exists():
            try:
                urllib.request.urlretrieve(url, dest)
                logger.info("Downloaded: %s.png", name)
                download_count += 1
            except Exception as e:
                logger.error("Failed to download %s: %s", name, e)

    # --- Generate VectorDrawable XMLs ---
    icon_dir = out_dir

    def inject_colors(comp_node):
        """Resolve paint style references in PATH fill to actual color values."""
        def traverse(n):
            if n.get("type") == "PATH":
                for p in n.get("path", []):
                    fill_key = p.get("fill")
                    if fill_key in all_styles:
                        style_val = all_styles[fill_key].get("value", [])
                        if style_val and isinstance(style_val[0], str):
                            p["fill"] = style_val[0]
            for c in n.get("children", []):
                traverse(c)
        traverse(comp_node)

    logger.info("Processing %d vector icons into XML...", len(icon_assets))
    rendered = 0

    # Deduplicate icons by name
    seen_icons = set()
    for icon in icon_assets:
        n = icon["name"]
        if n in seen_icons:
            continue
        seen_icons.add(n)

        comp = icon["node"]
        dest = icon_dir / f"{n}.xml"
        inject_colors(comp)

        if generate_vector_drawable(comp, str(dest)):
            rendered += 1

    if rendered > 0:
        logger.info("Generated %d VectorDrawable '.xml' files.", rendered)

    # --- Output missing components as structured JSON ---
    if missing_components:
        # Deduplicate by component_id
        seen_cids = set()
        unique_missing = []
        for mc in missing_components:
            if mc["component_id"] not in seen_cids:
                seen_cids.add(mc["component_id"])
                unique_missing.append(mc)

        missing_path = out_dir.parent / "missing_components.json"
        # Try to extract fileId from pipeline_result.json or file_context.json if available
        file_id = ""
        pipeline_res_path = out_dir.parent / "pipeline_result.json"
        context_path = out_dir.parent / "file_context.json"
        if pipeline_res_path.exists():
            try:
                with open(pipeline_res_path, "r", encoding="utf-8") as f:
                    pr_data = json.load(f)
                    file_id = pr_data.get("file_context", {}).get("fileId", "")
            except Exception:
                pass
        if not file_id and context_path.exists():
            try:
                with open(context_path, "r", encoding="utf-8") as f:
                    ctx = json.load(f)
                    file_id = ctx.get("fileId", "")
            except Exception:
                pass

        missing_data = {
            "file_id": file_id,
            "total_missing": len(unique_missing),
            "missing": unique_missing,
            "instruction": (
                "Use scripts/pipeline/getdsl_to_file.py with --file-id and --layer-id=component_id "
                "for ALL items. Save each result to comp_<component_id>.json "
                "with --skip-file-context, then re-run extract with all JSONs."
            ),
        }
        with open(missing_path, "w", encoding="utf-8") as f:
            json.dump(missing_data, f, indent=2, ensure_ascii=False)

        logger.warning("=" * 60)
        logger.warning(
            "MISSING %d COMPONENT MASTERS (see missing_components.json)", len(unique_missing)
        )
        logger.warning("=" * 60)
        for mc in unique_missing:
            logger.warning("  %s -> componentId: %s", mc["name"], mc["component_id"])
    else:
        logger.info("All icon components resolved. No missing masters.")

    if shared_library_icons:
        logger.info(
            "Reused %d shared widget-library icons via canonical drawable names.",
            len(shared_library_icons),
        )
        for icon_name in sorted(shared_library_icons):
            logger.info("  shared: %s", icon_name)

    # Summary
    logger.info("=" * 60)
    logger.info("EXTRACTION SUMMARY:")
    logger.info("  Raster images downloaded: %d", download_count)
    logger.info("  Vector icons generated:   %d", rendered)
    logger.info("  Shared library icons:    %d", len(shared_library_icons))
    logger.info("  Missing components:       %d", len(missing_components))
    logger.info("=" * 60)


def _is_icon_by_name(name: str) -> bool:
    """Check if a node name matches common icon naming patterns."""
    name_lower = name.lower()
    # Common icon prefixes/patterns from MasterGo component libraries
    patterns = ["ic_", "icon/", "/ic/", "ic/", "edit/ic_", "all/ic_", "media/ic_"]
    return any(p in name_lower for p in patterns)


# ---------------------------------------------------------------------------
# Subcommand: replace
# ---------------------------------------------------------------------------

def cmd_replace(args):
    """Replace @drawable/ph_icon_xxx placeholders in XML files with actual drawable names.
    
    Scans all XML files in layout_dir and substitutes placeholder references
    based on the generated icon files.
    """
    if len(args) < 2:
        print("Usage: python extract_assets.py replace <layout_dir> <manifest.json>")
        sys.exit(1)

    layout_dir = Path(args[0])
    manifest_path = args[1]

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Build replacement map: ph_icon_xxx -> actual drawable resource name.
    replacements = {}
    for icon in manifest.get("icon_placeholders", []):
        ph = icon.get("placeholder", "")
        if ph.startswith("@drawable/ph_icon_"):
            icon_name = ph.replace("@drawable/ph_icon_", "")
            actual_name = f"@drawable/{_canonical_icon_name(icon_name)}" if icon_name else ph
            replacements[ph] = actual_name

    if not replacements:
        logger.info("No icon placeholders found in manifest. Nothing to replace.")
        return

    logger.info("Replacing %d icon placeholders...", len(replacements))

    # Scan all XML files
    replaced_count = 0
    for xml_file in layout_dir.rglob("*.xml"):
        with open(xml_file, "r", encoding="utf-8") as f:
            content = f.read()

        original = content
        for old, new in replacements.items():
            content = content.replace(old, new)

        if content != original:
            with open(xml_file, "w", encoding="utf-8") as f:
                f.write(content)
            replaced_count += 1
            logger.info("  Updated: %s", xml_file.name)

    logger.info("Replaced icon placeholders in %d files.", replaced_count)


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        print("MasterGo Asset Extraction Pipeline v2")
        print()
        print("Usage:")
        print("  python extract_assets.py extract <output_dir> <input.json> [--manifest <manifest.json>]")
        print("  python extract_assets.py replace <layout_dir> <manifest.json>")
        sys.exit(1)

    subcommand = sys.argv[1]

    if subcommand == "extract":
        cmd_extract(sys.argv[2:])
    elif subcommand == "replace":
        cmd_replace(sys.argv[2:])
    else:
        print(f"Unknown subcommand: {subcommand}")
        print("Available: extract, replace")
        sys.exit(1)


if __name__ == "__main__":
    main()
