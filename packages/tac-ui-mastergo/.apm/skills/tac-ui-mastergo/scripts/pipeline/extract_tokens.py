"""
MasterGo Design Token Extractor (v2.0)
Extracts design tokens from MasterGo DSL styles: colors, typography, spacing.

Key differences from Figma token extractor:
  - Colors come from top-level styles.paint_* (with CSS color values)
  - Typography from styles.font_* (with family, size, lineHeight)
  - Effects from styles.effect_* (CSS box-shadow, blur)
  - Leverages MasterGo's `token` field for semantic naming

Output:
  - colors.xml       : All color tokens (merged with existing)
  - text_appearances.xml : Typography styles
  - dimens.xml       : Spacing, corner radius, elevation
  - token_registry.json : Summary for pipeline

Usage:
    python extract_tokens.py <mastergo_raw.json> <android_res_dir>
"""

import json
import logging
import os
import re
import sys
from typing import Any, Optional

# Add pipeline and parent scripts dir to path for imports
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from mastergo_utils import (
    css_color_to_hex,
    parse_css_gradient,
    resolve_paint,
    resolve_font,
    sanitize_resource_name,
)

logger = logging.getLogger(__name__)


def _load_data(input_path: str) -> dict:
    """Load MasterGo DSL data from JSON file."""
    with open(input_path, "r", encoding="utf-8") as f:
        return json.loads(f.read().strip())


# ---------------------------------------------------------------------------
# Color Extraction
# ---------------------------------------------------------------------------

def extract_colors(dsl: dict) -> dict[str, str]:
    """Extract all color tokens from MasterGo DSL styles.

    MasterGo stores colors in:
      styles.paint_* with value: ["#FFFFFF"] or ["rgba(...)"]

    Returns:
        Dict mapping color name -> hex value.
    """
    colors = {}
    styles = dsl.get("styles", {})

    for key, entry in styles.items():
        if not key.startswith("paint_"):
            continue

        values = entry.get("value", [])
        token = entry.get("token")

        if not values or not isinstance(values, list):
            continue

        first = values[0]

        # Skip image fills and empty values
        if isinstance(first, dict):
            continue
        if not isinstance(first, str):
            continue
        # Skip gradients (they go to drawables, not colors.xml)
        if "linear-gradient" in first:
            continue

        hex_color = css_color_to_hex(first)
        if not hex_color:
            continue

        # Use token name if available (more semantic), else use the paint key
        if token:
            # Convert "系统/Function/wt_system_function_green_color" -> token-based name
            # Take the last segment as the primary name
            segments = token.replace("/", "_").strip()
            name = sanitize_resource_name(segments)
        else:
            name = sanitize_resource_name(key)

        colors[name] = hex_color

    # Also walk nodes to find inline borderRadius-based colors etc.
    # (MasterGo nodes don't have inline fills -- they always reference paint keys)

    logger.info("Extracted %d color tokens from styles", len(colors))
    return colors


# ---------------------------------------------------------------------------
# Typography Extraction
# ---------------------------------------------------------------------------

def extract_typography(dsl: dict) -> list[dict]:
    """Extract typography styles from MasterGo DSL font styles.

    Returns:
        List of unique typography style definitions.
    """
    styles_dict = dsl.get("styles", {})
    result = []
    seen_signatures = set()

    for key, entry in styles_dict.items():
        if not key.startswith("font_"):
            continue

        value = entry.get("value", {})
        token = entry.get("token")

        if not isinstance(value, dict):
            continue

        family = value.get("family", "")
        size = value.get("size", 0)

        if not family or not size:
            continue

        # Parse lineHeight
        line_height_raw = value.get("lineHeight", "0")
        try:
            line_height = float(line_height_raw) if line_height_raw not in ("auto", "") else 0
        except (ValueError, TypeError):
            line_height = 0

        # Parse letterSpacing
        letter_spacing_raw = value.get("letterSpacing", "auto")
        letter_spacing = 0.0
        if isinstance(letter_spacing_raw, (int, float)):
            letter_spacing = float(letter_spacing_raw)
        elif isinstance(letter_spacing_raw, str) and letter_spacing_raw not in ("auto", "%", ""):
            try:
                letter_spacing = float(letter_spacing_raw)
            except ValueError:
                letter_spacing = 0.0

        # Infer weight from family name
        font_weight = _infer_weight(family, value.get("style", ""))

        # Deduplicate
        sig = f"{family}_{size}_{font_weight}_{line_height}_{letter_spacing}"
        if sig in seen_signatures:
            continue
        seen_signatures.add(sig)

        # Name: prefer token name, else generate from properties
        if token:
            style_name = sanitize_resource_name(token.replace("/", "_"))
        else:
            weight_name = _weight_to_name(font_weight)
            style_name = f"TextAppearance_{sanitize_resource_name(family)}_{weight_name}_{int(size)}sp"

        result.append({
            "name": style_name,
            "fontFamily": family,
            "fontSize": size,
            "fontWeight": font_weight,
            "lineHeight": line_height,
            "letterSpacing": letter_spacing,
            "sourceKey": key,
        })

    logger.info("Extracted %d unique typography styles", len(result))
    return result


def _infer_weight(family: str, style: str) -> int:
    """Infer font weight from family suffix or style field."""
    combined = (family + " " + style).lower()
    if "bold" in combined or family.endswith("B"):
        return 700
    if "semibold" in combined:
        return 600
    if "medium" in combined or family.endswith("M"):
        return 500
    if "light" in combined or family.endswith("L"):
        return 300
    if "thin" in combined:
        return 100
    return 400


def _weight_to_name(weight: int) -> str:
    """Convert numeric font weight to a human-readable name."""
    mapping = {
        100: "Thin", 200: "ExtraLight", 300: "Light",
        400: "Regular", 500: "Medium", 600: "SemiBold",
        700: "Bold", 800: "ExtraBold", 900: "Black",
    }
    return mapping.get(weight, f"W{weight}")


# ---------------------------------------------------------------------------
# Dimensions Extraction
# ---------------------------------------------------------------------------

def extract_dimensions(dsl: dict) -> dict[str, float]:
    """Extract reusable dimension values from MasterGo DSL nodes.

    Scans nodes for corner radii, spacing (from flex gap), and shadow elevations.

    Returns:
        Dict mapping dimen name -> dp value.
    """
    dimens = {}
    nodes = dsl.get("nodes", [])

    def _walk(node: dict):
        name_prefix = sanitize_resource_name(node.get("name", "node"))

        # Corner radius (e.g., "16px" or "12px")
        br = node.get("borderRadius")
        if br:
            # Parse "16px" or numeric
            val = _parse_px(br)
            if val and val > 0:
                dimens.setdefault(f"radius_{name_prefix}", val)

        # Flex gap
        flex = node.get("flexContainerInfo")
        if flex:
            gap_str = flex.get("gap", "0")
            gap_val = _parse_px(gap_str.split()[0] if " " in gap_str else gap_str)
            if gap_val and gap_val > 0:
                dimens.setdefault(f"spacing_{name_prefix}", gap_val)

        # Stroke width
        sw = node.get("strokeWidth")
        if sw:
            val = _parse_px(sw)
            if val and val > 0:
                dimens.setdefault(f"stroke_width_{name_prefix}", val)

        # Recurse
        for child in node.get("children", []):
            if isinstance(child, dict):
                _walk(child)

    for root in nodes:
        if isinstance(root, dict):
            _walk(root)

    # Extract from effects (shadow elevation)
    styles = dsl.get("styles", {})
    for key, entry in styles.items():
        if not key.startswith("effect_"):
            continue
        for css_str in entry.get("value", []):
            if isinstance(css_str, str) and "box-shadow" in css_str and "inset" not in css_str:
                # Parse blur radius as elevation
                m = re.search(r"box-shadow:.*?(\d+(?:\.\d+)?)px\s+\d+(?:\.\d+)?px\s+(rgba|#)", css_str)
                # Actually parse all 4 values
                m2 = re.match(
                    r"box-shadow:\s*[0-9.-]+px\s+[0-9.-]+px\s+([0-9.-]+)px",
                    css_str,
                )
                if m2:
                    blur = float(m2.group(1))
                    if blur > 0:
                        name = sanitize_resource_name(key)
                        dimens.setdefault(f"elevation_{name}", blur)

    logger.info("Extracted %d dimension tokens", len(dimens))
    return dimens


def _parse_px(value: Any) -> Optional[float]:
    """Parse a px value string to float. E.g., '16px' -> 16.0, '0px' -> 0."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        m = re.match(r"([0-9.]+)\s*(?:px)?", value)
        if m:
            return float(m.group(1))
    return None


# ---------------------------------------------------------------------------
# Android XML Generation
# ---------------------------------------------------------------------------

def generate_colors_patch_xml(colors: dict[str, str], work_dir: str) -> str:
    """Generate Android colors patch xml.
    
    Provides a patch file for developers/LLMs to selectively merge.
    """
    path = os.path.join(work_dir, "colors_patch.xml")
    xml = '<?xml version="1.0" encoding="utf-8"?>\n<!-- PATCH: Add these to res/values/colors.xml -->\n<resources>\n'
    
    for name in sorted(colors.keys()):
        safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        xml += f'    <color name="{safe_name}">{colors[name]}</color>\n'
        
    xml += '</resources>\n'

    os.makedirs(work_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)

    logger.info("Generated colors_patch.xml with %d colors at %s", len(colors), path)
    return path


def generate_text_appearances_patch_xml(styles: list[dict], work_dir: str) -> str:
    """Generate Android text_appearances patch xml from extracted typography."""
    xml = '<?xml version="1.0" encoding="utf-8"?>\n<!-- PATCH: Add these to res/values/text_appearances.xml -->\n<resources>\n'

    for style in styles:
        name = style["name"]
        font_size = int(style["fontSize"])
        font_weight = style["fontWeight"]

        line_height = style.get("lineHeight", 0)
        line_spacing_extra = max(0, int(line_height - font_size)) if line_height else 0

        letter_spacing_em = round(style.get("letterSpacing", 0) / font_size, 3) if font_size else 0

        font_family = style["fontFamily"].lower().replace(" ", "_")

        xml += f'    <style name="{name}" parent="TextAppearance.AppCompat">\n'
        xml += f'        <item name="android:textSize">{font_size}sp</item>\n'
        xml += f'        <item name="android:fontFamily">@font/{font_family}</item>\n'
        if font_weight != 400:
            xml += f'        <item name="android:textFontWeight">{font_weight}</item>\n'
        if line_spacing_extra > 0:
            xml += f'        <item name="android:lineSpacingExtra">{line_spacing_extra}dp</item>\n'
        if letter_spacing_em != 0:
            xml += f'        <item name="android:letterSpacing">{letter_spacing_em}</item>\n'
        xml += '    </style>\n\n'

    xml += '</resources>\n'

    os.makedirs(work_dir, exist_ok=True)
    path = os.path.join(work_dir, "text_appearances_patch.xml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)

    logger.info("Generated text_appearances_patch.xml with %d styles at %s", len(styles), path)
    return path


def generate_dimens_patch_xml(dimens: dict[str, float], work_dir: str) -> str:
    """Generate Android dimens patch xml from extracted dimensions."""
    xml = '<?xml version="1.0" encoding="utf-8"?>\n<!-- PATCH: Add these to res/values/dimens.xml -->\n<resources>\n'

    for name in sorted(dimens.keys()):
        safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        val = int(dimens[name]) if dimens[name] == int(dimens[name]) else dimens[name]
        xml += f'    <dimen name="{safe_name}">{val}dp</dimen>\n'

    xml += '</resources>\n'

    os.makedirs(work_dir, exist_ok=True)
    path = os.path.join(work_dir, "dimens_patch.xml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)

    logger.info("Generated dimens_patch.xml with %d dimensions at %s", len(dimens), path)
    return path


# ---------------------------------------------------------------------------
# Main: Extract All Tokens
# ---------------------------------------------------------------------------

def extract_all_tokens(input_path: str, res_dir: str) -> dict:
    """Full token extraction pipeline for MasterGo DSL.

    Args:
        input_path: Path to raw MasterGo DSL JSON file.
        res_dir: Path to Android res/values/ directory (preserved for API compatibility, but patches are routed to work_dir).

    Returns:
        Token registry dict.
    """
    data = _load_data(input_path)
    dsl = data.get("dsl", data)
    
    work_dir = os.path.dirname(input_path) or "."
    os.makedirs(work_dir, exist_ok=True)

    colors = extract_colors(dsl)
    typography = extract_typography(dsl)
    dimens = extract_dimensions(dsl)

    colors_path = generate_colors_patch_xml(colors, work_dir)
    typography_path = generate_text_appearances_patch_xml(typography, work_dir)
    dimens_path = generate_dimens_patch_xml(dimens, work_dir)

    registry = {
        "summary": {
            "color_count": len(colors),
            "type_count": len(typography),
            "dimen_count": len(dimens),
        },
        "colors": colors,
        "typography": [
            {"name": s["name"], "fontFamily": s["fontFamily"],
             "fontSize": s["fontSize"], "fontWeight": s["fontWeight"]}
            for s in typography
        ],
        "dimensions": dimens,
        "generated_files": {
            "colors_patch_xml": colors_path,
            "text_appearances_patch_xml": typography_path,
            "dimens_patch_xml": dimens_path,
        },
    }

    return registry


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        print("Usage: python extract_tokens.py <mastergo_raw.json> <android_res_dir>")
        sys.exit(1)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    input_path = sys.argv[1]
    res_dir = sys.argv[2]

    try:
        registry = extract_all_tokens(input_path, res_dir)
        registry_path = os.path.join(os.path.dirname(input_path), "token_registry.json")
        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)

        print(json.dumps({
            "status": "success",
            "registry_file": registry_path,
            **registry["summary"],
        }, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
