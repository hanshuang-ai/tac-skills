"""
MasterGo Utility Functions (v2.0)
Shared helpers for resolving MasterGo DSL style references (paint, font, effect),
CSS color conversion, and Android resource name sanitization.

MasterGo DSL uses a global `styles` dict with keyed references:
  - paint_*  : colors, gradients, images
  - font_*   : typography definitions
  - effect_* : shadows, blurs
Nodes reference these via string keys (e.g., fill: "paint_4:709").
"""

import re
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CSS Color Conversion
# ---------------------------------------------------------------------------

def css_color_to_hex(css_str: str) -> Optional[str]:
    """Converts CSS color strings to Android hex format (#AARRGGBB or #RRGGBB).

    Handles:
      - '#RRGGBB', '#RGB'
      - 'rgba(R, G, B, A)'
      - 'rgb(R, G, B)'

    Args:
        css_str: A CSS color string.

    Returns:
        Android-format hex string, or None if unparseable.
    """
    if not isinstance(css_str, str):
        logger.warning("css_color_to_hex received non-string: %s (type=%s)", css_str, type(css_str))
        return None

    css_str = css_str.strip()

    # Already hex
    if css_str.startswith("#"):
        # Normalize short hex (#RGB -> #RRGGBB)
        if len(css_str) == 4:
            r, g, b = css_str[1], css_str[2], css_str[3]
            return f"#{r}{r}{g}{g}{b}{b}".upper()
        if len(css_str) in (7, 9):
            return css_str.upper()
        return css_str.upper()

    # rgba(R, G, B, A)
    m = re.match(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9.]+)\s*\)", css_str)
    if m:
        r_int = max(0, min(255, int(m.group(1))))
        g_int = max(0, min(255, int(m.group(2))))
        b_int = max(0, min(255, int(m.group(3))))
        alpha = max(0, min(255, int(float(m.group(4)) * 255)))
        if alpha == 255:
            return f"#{r_int:02X}{g_int:02X}{b_int:02X}"
        return f"#{alpha:02X}{r_int:02X}{g_int:02X}{b_int:02X}"

    # rgb(R, G, B)
    m_rgb = re.match(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", css_str)
    if m_rgb:
        r_int = max(0, min(255, int(m_rgb.group(1))))
        g_int = max(0, min(255, int(m_rgb.group(2))))
        b_int = max(0, min(255, int(m_rgb.group(3))))
        return f"#{r_int:02X}{g_int:02X}{b_int:02X}"

    logger.debug("css_color_to_hex could not parse: '%s'", css_str)
    return None


# ---------------------------------------------------------------------------
# Gradient Parsing
# ---------------------------------------------------------------------------

def parse_css_gradient(gradient_str: str) -> Optional[dict]:
    """Parses a CSS linear-gradient string into a structured representation.

    Example input: "linear-gradient(180deg, rgba(0, 0, 0, 0) 12%, rgba(0, 0, 0, 0.2) 130%)"

    Returns:
        Dict with gradient info: {type, angle, stops: [{color, position}, ...]},
        or None if not parseable.
    """
    if not isinstance(gradient_str, str) or "linear-gradient" not in gradient_str:
        return None

    m = re.match(r"linear-gradient\(\s*(\d+)deg\s*,\s*(.+)\)", gradient_str)
    if not m:
        return None

    angle = int(m.group(1))
    stops_str = m.group(2)

    stops = []
    # Match each color stop: "rgba(...) XX%" or "#XXXXXX XX%"
    parts = re.findall(r"(rgba?\([^)]+\)|#[0-9a-fA-F]+)\s+(\d+)%", stops_str)
    for color_str, pos_str in parts:
        hex_color = css_color_to_hex(color_str)
        if hex_color:
            stops.append({
                "color": hex_color,
                "position": int(pos_str) / 100.0,
            })

    if not stops:
        return None

    return {
        "type": "linear",
        "angle": angle,
        "stops": stops,
    }


# ---------------------------------------------------------------------------
# MasterGo Style Reference Resolution
# ---------------------------------------------------------------------------

def resolve_paint(paint_ref: str, styles: dict) -> Optional[dict]:
    """Resolves a MasterGo paint reference to its actual value.

    MasterGo paint values can be:
      - Solid color: ["#FFFFFF"] or ["rgba(255, 255, 255, 0.4)"]
      - Gradient: ["linear-gradient(180deg, ...)"]
      - Image: [{url: "https://...", filters: ""}]
      - Empty: []

    Args:
        paint_ref: Paint style key like "paint_4:709".
        styles: The global styles dict from MasterGo DSL.

    Returns:
        Dict with resolved paint info:
          {type: "solid|gradient|image|empty", value: ..., token: ...}
        or None if reference not found.
    """
    if not paint_ref or not isinstance(paint_ref, str):
        return None

    style_entry = styles.get(paint_ref)
    if style_entry is None:
        logger.debug("resolve_paint: paint ref '%s' not found in styles", paint_ref)
        return None

    values = style_entry.get("value", [])
    token = style_entry.get("token")

    # Empty paint
    if not values or (isinstance(values, list) and len(values) == 0):
        return {"type": "empty", "value": None, "token": token}

    if isinstance(values, list) and len(values) > 0:
        first = values[0]

        # Image fill: {url: "...", filters: ""}
        if isinstance(first, dict) and "url" in first:
            return {
                "type": "image",
                "value": first["url"],
                "token": token,
            }

        # String-based values
        if isinstance(first, str):
            # Gradient
            if "linear-gradient" in first:
                gradient = parse_css_gradient(first)
                # If multiple gradient layers, parse all
                all_gradients = []
                for v in values:
                    if isinstance(v, str) and "linear-gradient" in v:
                        g = parse_css_gradient(v)
                        if g:
                            all_gradients.append(g)
                return {
                    "type": "gradient",
                    "value": all_gradients if len(all_gradients) > 1 else gradient,
                    "token": token,
                }

            # Solid color (hex or rgba)
            hex_color = css_color_to_hex(first)
            if hex_color:
                return {
                    "type": "solid",
                    "value": hex_color,
                    "token": token,
                }

    logger.debug("resolve_paint: could not resolve paint ref '%s', values=%s", paint_ref, values)
    return None


def resolve_font(font_ref: str, styles: dict) -> Optional[dict]:
    """Resolves a MasterGo font reference to its actual typography properties.

    MasterGo font values: {
        family: "AlibabaPuHuiTiR",
        size: 28,
        style: "",
        decoration: "none",
        case: "none",
        lineHeight: "40",
        letterSpacing: "auto"
    }

    Args:
        font_ref: Font style key like "font_4:0700".
        styles: The global styles dict.

    Returns:
        Dict with font properties, or None if not found.
    """
    if not font_ref or not isinstance(font_ref, str):
        return None

    style_entry = styles.get(font_ref)
    if style_entry is None:
        logger.debug("resolve_font: font ref '%s' not found in styles", font_ref)
        return None

    value = style_entry.get("value", {})
    token = style_entry.get("token")

    if not isinstance(value, dict):
        return None

    # Parse lineHeight (can be string "40" or numeric)
    line_height_raw = value.get("lineHeight", "0")
    try:
        line_height = float(line_height_raw) if line_height_raw != "auto" else 0
    except (ValueError, TypeError):
        line_height = 0

    # Parse letterSpacing (can be "auto", "%", or numeric)
    letter_spacing_raw = value.get("letterSpacing", "auto")
    letter_spacing = 0.0
    if isinstance(letter_spacing_raw, (int, float)):
        letter_spacing = float(letter_spacing_raw)
    elif isinstance(letter_spacing_raw, str) and letter_spacing_raw not in ("auto", "%", ""):
        try:
            letter_spacing = float(letter_spacing_raw)
        except ValueError:
            letter_spacing = 0.0

    return {
        "fontFamily": value.get("family", ""),
        "fontSize": value.get("size", 0),
        "fontStyle": value.get("style", ""),
        "fontWeight": _infer_weight_from_family(value.get("family", ""), value.get("style", "")),
        "lineHeight": line_height,
        "letterSpacing": letter_spacing,
        "decoration": value.get("decoration", "none"),
        "textCase": value.get("case", "none"),
        "token": token,
    }


def _infer_weight_from_family(family: str, style: str) -> int:
    """Infer font weight from MasterGo font family name suffix or style field.

    MasterGo encodes weight in the family name:
      AlibabaPuHuiTiR -> Regular (400)
      AlibabaPuHuiTiM -> Medium (500)
      AlibabaPuHuiTiB -> Bold (700)
      AlibabaPuHuiTi  -> Regular (400), check style field
    """
    combined = (family + " " + style).lower()

    if "bold" in combined or family.endswith("B"):
        return 700
    if "semibold" in combined or "semi" in combined:
        return 600
    if "medium" in combined or family.endswith("M"):
        return 500
    if "light" in combined or family.endswith("L"):
        return 300
    if "thin" in combined:
        return 100
    # Default: Regular
    return 400


def resolve_effect(effect_ref: str, styles: dict) -> Optional[list]:
    """Resolves a MasterGo effect reference to structured effect definitions.

    MasterGo effect values are CSS strings like:
      - "box-shadow: 0px 3px 27px 0px rgba(0, 0, 0, 0.2022);"
      - "backdrop-filter: blur(200px);"
      - "filter: blur(10.42px);"

    Args:
        effect_ref: Effect style key like "effect_4:669".
        styles: The global styles dict.

    Returns:
        List of effect dicts, or None if not found.
    """
    if not effect_ref or not isinstance(effect_ref, str):
        return None

    style_entry = styles.get(effect_ref)
    if style_entry is None:
        logger.debug("resolve_effect: effect ref '%s' not found in styles", effect_ref)
        return None

    values = style_entry.get("value", [])
    token = style_entry.get("token")
    effects = []

    for css_str in values:
        if not isinstance(css_str, str):
            continue

        # Box shadow: "box-shadow: Xpx Ypx Rpx Spx color;"
        box_m = re.match(
            r"box-shadow:\s*(inset\s+)?([0-9.-]+)px\s+([0-9.-]+)px\s+([0-9.-]+)px\s+([0-9.-]+)px\s+(rgba?\([^)]+\)|#[0-9a-fA-F]+)",
            css_str,
        )
        if box_m:
            inset = box_m.group(1) is not None
            effects.append({
                "type": "INNER_SHADOW" if inset else "DROP_SHADOW",
                "offset_x": float(box_m.group(2)),
                "offset_y": float(box_m.group(3)),
                "radius": float(box_m.group(4)),
                "spread": float(box_m.group(5)),
                "color": css_color_to_hex(box_m.group(6)),
                "token": token,
            })
            continue

        # Backdrop blur: "backdrop-filter: blur(Xpx);"
        blur_m = re.match(r"backdrop-filter:\s*blur\(([0-9.]+)px\)", css_str)
        if blur_m:
            effects.append({
                "type": "BACKDROP_BLUR",
                "radius": float(blur_m.group(1)),
                "token": token,
            })
            continue

        # Layer blur: "filter: blur(Xpx);"
        filter_m = re.match(r"filter:\s*blur\(([0-9.]+)px\)", css_str)
        if filter_m:
            effects.append({
                "type": "LAYER_BLUR",
                "radius": float(filter_m.group(1)),
                "token": token,
            })
            continue

        logger.debug("resolve_effect: unrecognized CSS effect: '%s'", css_str)

    return effects if effects else None


# ---------------------------------------------------------------------------
# Resource Name Sanitization
# ---------------------------------------------------------------------------

def sanitize_resource_name(name: str) -> str:
    """Converts a MasterGo node name to a valid Android resource name.

    Android resource names: lowercase, alphanumeric, underscores only.
    """
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    sanitized = re.sub(r"_+", "_", sanitized)  # Collapse multiple underscores
    sanitized = sanitized.strip("_").lower()

    # Ensure it doesn't start with a digit
    if sanitized and sanitized[0].isdigit():
        sanitized = "n_" + sanitized

    return sanitized or "unnamed"
