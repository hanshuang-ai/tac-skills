"""
MasterGo Skeleton Tree Extractor (v2.3)

Extracts a lightweight topological skeleton from the full MasterGo DSL.
The skeleton preserves ONLY structural information needed for global component
decomposition, stripping all visual details (fills, strokes, effects, text content, etc.).

Key features:
  - ~85%+ compression ratio (e.g. 137KB -> ~15KB)
  - Leaf type semantic tagging (IMAGE/TEXT/ICON/SHAPE)
  - Overlap detection for guiding ViewGroup selection
  - componentId preservation for homogeneous component detection

Usage:
    python extract_skeleton.py <mastergo_raw.json> <output_path>
    
    # Or as a library:
    from extract_skeleton import extract_skeleton
    skeleton = extract_skeleton("mastergo_raw.json")
"""

import json
import logging
import os
import sys

# Ensure UTF-8 output to avoid Chinese gibberish in Windows console
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Thresholds for leaf type classification
ICON_MAX_SIZE = 64  # px -- PATH nodes smaller than this are classified as ICON

# Minimum overlap ratio to flag has_overlap
OVERLAP_THRESHOLD = 0.1  # 10% of the smaller node's area

# Name truncation limit (chars)
NAME_MAX_LEN = 20

# Type abbreviation map -- saves ~40% on the 'type' field
TYPE_ABBR = {
    "FRAME": "F",
    "GROUP": "G",
    "INSTANCE": "I",
    "TEXT": "T",
    "PATH": "P",
    "SVG_ELLIPSE": "E",
    "LAYER": "L",
}


# ---------------------------------------------------------------------------
# Core Logic
# ---------------------------------------------------------------------------

def _classify_leaf_type(node: dict, width: float, height: float) -> str:
    """Classify a leaf node into a semantic type.

    Args:
        node: Raw DSL node dict.
        width: Node width in px.
        height: Node height in px.

    Returns:
        One of: IMAGE, TEXT, ICON, SHAPE
    """
    node_type = node.get("type", "")

    # TEXT nodes are always classified as TEXT
    if node_type == "TEXT" or node.get("text"):
        return "TEXT"

    # PATH / SVG nodes with small size -> ICON
    if node_type == "PATH":
        if width < ICON_MAX_SIZE and height < ICON_MAX_SIZE:
            return "ICON"

    # Check for image fill (paint_* with URL in styles would be resolved elsewhere,
    # but we can detect image-type fills heuristically)
    fill = node.get("fill")
    if fill and isinstance(fill, str) and fill.startswith("paint_"):
        # Nodes with image fills that are not tiny icons are likely images
        if width > ICON_MAX_SIZE or height > ICON_MAX_SIZE:
            return "IMAGE"

    # SVG_ELLIPSE -> SHAPE
    if node_type == "SVG_ELLIPSE":
        return "SHAPE"

    # Default: SHAPE for PATH, IMAGE for FRAME/GROUP with fills
    if node_type == "PATH":
        return "SHAPE"

    # FRAME/GROUP with large dimensions and a fill -> likely an IMAGE container
    if fill and (width > 100 or height > 100):
        return "IMAGE"

    return "SHAPE"


def _check_children_overlap(children: list) -> bool:
    """Check if any pair of children has overlapping bounding boxes.

    Uses relativeX/Y + width/height from layoutStyle.
    Overlap indicates the parent should use FrameLayout or ConstraintLayout
    rather than LinearLayout.

    Args:
        children: List of raw DSL node dicts.

    Returns:
        True if any pair of children overlaps significantly.
    """
    if len(children) < 2:
        return False

    # Extract bounding boxes
    boxes = []
    for child in children:
        ls = child.get("layoutStyle", {})
        x = ls.get("relativeX", 0) or 0
        y = ls.get("relativeY", 0) or 0
        w = ls.get("width", 0) or 0
        h = ls.get("height", 0) or 0
        if w > 0 and h > 0:
            boxes.append((x, y, x + w, y + h, w * h))

    # Pairwise overlap check (O(n^2), acceptable for typical child counts < 20)
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            x1, y1, x2, y2, area_i = boxes[i]
            x3, y3, x4, y4, area_j = boxes[j]

            # Calculate intersection
            ix1:float = max(x1, x3)
            iy1:float = max(y1, y3)
            ix2:float = min(x2, x4)
            iy2:float = min(y2, y4)

            if ix1 < ix2 and iy1 < iy2:
                intersection = (ix2 - ix1) * (iy2 - iy1)
                smaller_area = min(area_i, area_j)
                if smaller_area > 0 and intersection / smaller_area > OVERLAP_THRESHOLD:
                    return True

    return False


def _get_actual_text(node: dict) -> str:
    """Extract text content from a text node or its children."""
    if node.get("type") == "TEXT":
        text_data = node.get("text", [])
        if isinstance(text_data, list):
            return "".join([str(segment.get("text", "")) for segment in text_data if isinstance(segment, dict)])
        elif isinstance(text_data, str):
            return text_data
    
    # Recurse into children
    first_child_text = ""
    for child in node.get("children", []):
        child_text = _get_actual_text(child)
        if child_text and not first_child_text:
            first_child_text = child_text
            
    return first_child_text

def _count_descendants(node: dict) -> int:
    """Count total descendant nodes (excluding self)."""
    total = 0
    for child in node.get("children", []):
        total += 1 + _count_descendants(child)
    return total


def _prune_node(node: dict, styles: dict, depth: int = 0) -> dict:
    """Recursively prune a DSL node into a skeleton node.

    Optimization strategies for maximum compression:
    1. INSTANCE nodes are collapsed: their internal children are NOT expanded
       (they are component-defined and the skeleton only needs the INSTANCE shell).
       Instead, a 'cc' (children_count) field records descendant count.
    2. Type is abbreviated (FRAME->F, GROUP->G, INSTANCE->I, etc.).
    3. Name is truncated to NAME_MAX_LEN characters.
    4. Dimensions are rounded to integers.
    5. componentId is only kept on INSTANCE nodes (the only type that has it).

    Args:
        node: Raw DSL node dict.
        styles: The top-level styles dict (for resolving fill type).
        depth: Current recursion depth.

    Returns:
        Pruned skeleton node dict.
    """
    skeleton = {}
    node_type = node.get("type", "")

    # -- Core identity --
    skeleton["id"] = node.get("id", "")
    skeleton["t"] = TYPE_ABBR.get(node_type, node_type)

    # Use actual text if available, fallback to container name
    actual_text = _get_actual_text(node)
    name = actual_text if actual_text else node.get("name", "")
    if name:
        skeleton["n"] = name[:NAME_MAX_LEN]

    # -- Dimensions (from layoutStyle, rounded to int for compactness) --
    ls = node.get("layoutStyle", {})
    width = ls.get("width", 0) or 0
    height = ls.get("height", 0) or 0
    skeleton["w"] = round(width)
    skeleton["h"] = round(height)

    # -- Children --
    raw_children = node.get("children", [])

    if raw_children:
        # INSTANCE optimization: collapse internal structure into a summary.
        # The INSTANCE's internals are defined by the component, not the page.
        # For blueprint analysis, we only need to know it exists, its size,
        # and its componentId for homogeneous detection.
        if node_type == "INSTANCE":
            skeleton["cc"] = _count_descendants(node)
            comp_id = node.get("componentId")
            if comp_id:
                skeleton["cid"] = comp_id
            # Do NOT recurse into INSTANCE children
        else:
            # Check overlap among direct children
            if _check_children_overlap(raw_children):
                skeleton["ol"] = True  # ol = overlap

            # Recurse into children
            skeleton["ch"] = [
                _prune_node(child, styles, depth + 1)
                for child in raw_children
            ]
    else:
        # Leaf node: classify type
        skeleton["lt"] = _classify_leaf_type(node, width, height)

    return skeleton


def extract_skeleton(input_path: str) -> dict:
    """Extract a lightweight skeleton tree from raw MasterGo DSL.

    Args:
        input_path: Path to mastergo_raw.json file.

    Returns:
        Dict with skeleton tree and metadata.
    """
    logger.info("Loading raw DSL from: %s", input_path)
    with open(input_path, "r", encoding="utf-8") as f:
        raw = json.loads(f.read().strip())

    dsl = raw.get("dsl", raw)
    styles = dsl.get("styles", {})
    nodes = dsl.get("nodes", [])

    if not nodes:
        logger.warning("No nodes found in DSL data")
        return {"metadata": {"total_nodes": 0}, "skeleton": None}

    root = nodes[0]

    # Count total nodes before pruning
    def _count(n):
        return 1 + sum(_count(c) for c in n.get("children", []))

    total_before = _count(root)
    raw_size = len(json.dumps(root, ensure_ascii=False).encode("utf-8"))

    # Prune
    skeleton = _prune_node(root, styles)

    # Calculate compression stats
    skeleton_size = len(json.dumps(skeleton, ensure_ascii=False).encode("utf-8"))
    compression = round((1 - skeleton_size / raw_size) * 100, 1) if raw_size > 0 else 0

    logger.info(
        "Skeleton extracted: %d nodes, %d bytes -> %d bytes (%.1f%% compression)",
        total_before, raw_size, skeleton_size, compression,
    )

    return {
        "metadata": {
            "total_nodes": total_before,
            "raw_size_bytes": raw_size,
            "skeleton_size_bytes": skeleton_size,
            "compression_percent": compression,
            "styles_count": len(styles),
        },
        "skeleton": skeleton,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        print("Usage: python extract_skeleton.py <mastergo_raw.json> <output_path>")
        print()
        print("Extracts a lightweight skeleton tree from MasterGo DSL data.")
        print("The skeleton preserves only structural topology for component analysis.")
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    result = extract_skeleton(input_path)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(json.dumps(result["metadata"], indent=2))


if __name__ == "__main__":
    main()
