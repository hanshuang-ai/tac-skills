"""
Android Layout Lint (v2.0)
Automated detection of common Android XML anti-patterns defined in SKILL.md Section 5.
Detects machine-checkable rules: 5.1, 5.4, 5.5, 5.7.

Output: lint_report.json with violations and PASS/FAIL verdict.

Usage:
    python lint_layout.py <layout.xml> [--output lint_report.json]
"""

import json
import logging
import os
import re
import sys
from typing import Optional
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)

# Android XML namespace
ANDROID_NS = "http://schemas.android.com/apk/res/android"
APP_NS = "http://schemas.android.com/apk/res-auto"

# Register namespaces so output preserves them
ET.register_namespace("android", ANDROID_NS)
ET.register_namespace("app", APP_NS)


class Violation:
    """Represents a single lint violation."""

    def __init__(self, rule: str, severity: str, line: int,
                 element_tag: str, message: str):
        self.rule = rule
        self.severity = severity
        self.line = line
        self.element_tag = element_tag
        self.message = message

    def to_dict(self) -> dict:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "line": self.line,
            "element_tag": self.element_tag,
            "message": self.message,
        }


# ---------------------------------------------------------------------------
# Line Number Tracking
# ---------------------------------------------------------------------------

def _parse_xml_with_lines(xml_path: str) -> tuple[Optional[ET.Element], dict]:
    """Parse XML and track element line numbers.

    Returns:
        Tuple of (root Element, {element -> line_number} mapping).
    """
    line_map = {}

    class LineTrackingParser(ET.XMLParser):
        pass

    # Parse with line tracking
    # ET doesn't natively support line numbers, so we use a workaround:
    # Read file line by line and match tags to approximate line positions
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError as e:
        logger.error("XML parse error in %s: %s", xml_path, e)
        return None, {}

    # Build approximate line number map by scanning raw text
    with open(xml_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Simple heuristic: map tags to their first occurrence line
    tag_line_cache = {}
    for i, line_text in enumerate(lines, 1):
        # Find XML tags in this line
        for match in re.finditer(r"<([a-zA-Z][a-zA-Z0-9_.]*)", line_text):
            tag = match.group(1)
            if tag not in tag_line_cache:
                tag_line_cache[tag] = []
            tag_line_cache[tag].append(i)

    # Map each element to its approximate line number
    tag_counters = {}
    for elem in root.iter():
        tag = elem.tag
        if tag not in tag_counters:
            tag_counters[tag] = 0
        idx = tag_counters[tag]
        tag_counters[tag] += 1

        available_lines = tag_line_cache.get(tag, [])
        if idx < len(available_lines):
            line_map[elem] = available_lines[idx]
        else:
            line_map[elem] = 0

    return root, line_map


# ---------------------------------------------------------------------------
# Rule Checkers
# ---------------------------------------------------------------------------

def check_rule_5_1(root: ET.Element, line_map: dict) -> list[Violation]:
    """Rule 5.1: Container Height -- Prefer wrap_content over fixed dp.

    Detects: Container with fixed dp height that contains TextView children.
    """
    violations = []
    container_types = {
        "LinearLayout", "FrameLayout", "RelativeLayout",
        "ConstraintLayout", "androidx.constraintlayout.widget.ConstraintLayout",
        "androidx.appcompat.widget.LinearLayoutCompat",
    }

    for elem in root.iter():
        tag = _short_tag(elem.tag)
        if tag not in container_types:
            continue

        height = elem.get(f"{{{ANDROID_NS}}}layout_height", "")

        # Check if height is a fixed dp value
        if not re.match(r"\d+dp", height):
            continue

        # Check if this container has any TEXT-displaying children
        has_text_child = False
        for child in elem:
            child_tag = _short_tag(child.tag)
            if child_tag in ("TextView", "EditText", "Button",
                             "com.google.android.material.button.MaterialButton",
                             "com.google.android.material.textfield.TextInputLayout"):
                has_text_child = True
                break
            # Also check nested text
            for grandchild in child.iter():
                if _short_tag(grandchild.tag) in ("TextView", "EditText"):
                    has_text_child = True
                    break

        if has_text_child:
            violations.append(Violation(
                rule="5.1",
                severity="warning",
                line=line_map.get(elem, 0),
                element_tag=tag,
                message=(
                    f"Container '{tag}' has fixed height '{height}' but contains "
                    f"text views. Use 'wrap_content' to avoid text clipping."
                ),
            ))

    return violations


def check_rule_5_4(root: ET.Element, line_map: dict) -> list[Violation]:
    """Rule 5.4: MaterialComponents -- <Button> ignores android:background.

    Detects: <Button> with android:background attribute.
    """
    violations = []

    for elem in root.iter():
        tag = _short_tag(elem.tag)
        if tag != "Button":
            continue

        has_background = elem.get(f"{{{ANDROID_NS}}}background") is not None
        if has_background:
            violations.append(Violation(
                rule="5.4",
                severity="error",
                line=line_map.get(elem, 0),
                element_tag="Button",
                message=(
                    "<Button> with android:background is ignored in MaterialComponents theme. "
                    "Use MaterialButton with app:backgroundTint, or use "
                    "style='@style/Widget.MaterialComponents.Button.OutlinedButton' for outlined style."
                ),
            ))

    return violations


def check_rule_5_5(root: ET.Element, line_map: dict) -> list[Violation]:
    """Rule 5.5: Circular Images -- Requires ShapeableImageView.

    Detects: Plain ImageView with shapeAppearanceOverlay attribute.
    """
    violations = []

    for elem in root.iter():
        tag = _short_tag(elem.tag)
        if tag != "ImageView":
            continue

        has_shape_overlay = elem.get(f"{{{APP_NS}}}shapeAppearanceOverlay") is not None
        if has_shape_overlay:
            violations.append(Violation(
                rule="5.5",
                severity="error",
                line=line_map.get(elem, 0),
                element_tag="ImageView",
                message=(
                    "shapeAppearanceOverlay only works on ShapeableImageView, not plain ImageView. "
                    "Replace with com.google.android.material.imageview.ShapeableImageView."
                ),
            ))

    return violations


def check_rule_5_7_heuristic(root: ET.Element, line_map: dict) -> list[Violation]:
    """Rule 5.7: Dynamic Lists -- Avoid hardcoded static items.

    Heuristic: Detects 4+ sibling ImageView/Views at the same nesting level
    with similar naming patterns (suggesting a repeated list that should be RecyclerView).
    """
    violations = []
    THRESHOLD = 4

    for parent in root.iter():
        children = list(parent)
        if len(children) < THRESHOLD:
            continue

        # Group children by tag
        tag_groups = {}
        for child in children:
            tag = _short_tag(child.tag)
            if tag not in tag_groups:
                tag_groups[tag] = []
            tag_groups[tag].append(child)

        for tag, group in tag_groups.items():
            if len(group) < THRESHOLD:
                continue

            # Check if they have sequentially numbered IDs (e.g., item_1, item_2, ...)
            ids = [g.get(f"{{{ANDROID_NS}}}id", "") for g in group]
            numbered = sum(1 for i in ids if re.search(r"_\d+$", i))
            if numbered >= THRESHOLD:
                violations.append(Violation(
                    rule="5.7",
                    severity="warning",
                    line=line_map.get(group[0], 0),
                    element_tag=_short_tag(parent.tag),
                    message=(
                        f"Found {len(group)} sibling '{tag}' elements with numbered IDs -- "
                        f"this looks like a hardcoded list. Consider using RecyclerView "
                        f"with a reusable item layout instead."
                    ),
                ))

    return violations


def check_rule_5_12(root: ET.Element, line_map: dict) -> list[Violation]:
    """Rule 5.12: Container Selection Priority -- prefer lightest container.

    Detects: ConstraintLayout with 0 or 1 direct children, which should
    use FrameLayout instead for lower overhead.
    """
    violations = []
    constraint_tags = {
        "ConstraintLayout",
        "androidx.constraintlayout.widget.ConstraintLayout",
    }

    for elem in root.iter():
        tag = _short_tag(elem.tag)
        if tag not in constraint_tags:
            continue

        child_count = len(list(elem))
        if child_count <= 1:
            violations.append(Violation(
                rule="5.12",
                severity="warning",
                line=line_map.get(elem, 0),
                element_tag=elem.tag,
                message=(
                    f"ConstraintLayout has only {child_count} child(ren). "
                    f"Use FrameLayout for single-child containers to reduce overhead."
                ),
            ))

    return violations


def check_rule_5_13(root: ET.Element, line_map: dict) -> list[Violation]:
    """Rule 5.13: Overdraw Prevention -- parent and child both with background.

    Detects: A ViewGroup with android:background whose direct child also
    has android:background, causing the GPU to draw the same pixel twice.
    """
    violations = []
    bg_attr = f"{{{ANDROID_NS}}}background"

    for parent in root.iter():
        parent_bg = parent.get(bg_attr)
        if not parent_bg:
            continue

        for child in parent:
            child_bg = child.get(bg_attr)
            if child_bg:
                violations.append(Violation(
                    rule="5.13",
                    severity="warning",
                    line=line_map.get(child, 0),
                    element_tag=_short_tag(child.tag),
                    message=(
                        f"Both parent '{_short_tag(parent.tag)}' (bg={parent_bg}) and "
                        f"child '{_short_tag(child.tag)}' (bg={child_bg}) define "
                        f"android:background, causing overdraw. Remove the parent "
                        f"background or make it transparent if the child fully covers it."
                    ),
                ))

    return violations


def check_rule_5_14(root: ET.Element, line_map: dict) -> list[Violation]:
    """Rule 5.14: View Hierarchy Depth Limit -- max 5 levels for AI-generated code.

    Recursively measures the deepest nesting level. Android Lint defaults to 10,
    but we enforce a stricter limit of 5 for AI-generated layouts.
    """
    violations = []
    MAX_DEPTH = 5

    def _measure_depth(elem: ET.Element, current_depth: int) -> int:
        """Returns the maximum depth found below this element."""
        children = list(elem)
        if not children:
            return current_depth
        return max(_measure_depth(c, current_depth + 1) for c in children)

    max_depth = _measure_depth(root, 1)
    if max_depth > MAX_DEPTH:
        violations.append(Violation(
            rule="5.14",
            severity="warning",
            line=1,
            element_tag=_short_tag(root.tag),
            message=(
                f"View hierarchy depth is {max_depth} levels (limit: {MAX_DEPTH}). "
                f"Deep nesting causes performance degradation during measure/layout passes. "
                f"Flatten the hierarchy using ConstraintLayout or extract sub-trees via <include>."
            ),
        ))

    return violations


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _short_tag(tag: str) -> str:
    """Extract short class name from fully qualified tag.

    E.g., 'com.google.android.material.button.MaterialButton' -> 'MaterialButton'
    """
    return tag.rsplit(".", 1)[-1] if "." in tag else tag


# ---------------------------------------------------------------------------
# Main Lint Runner
# ---------------------------------------------------------------------------

def lint_layout(xml_path: str) -> dict:
    """Run all lint checks on an Android layout XML file.

    Args:
        xml_path: Path to the XML layout file.

    Returns:
        Lint report dict with violations and verdict.
    """
    root, line_map = _parse_xml_with_lines(xml_path)

    if root is None:
        return {
            "file": xml_path,
            "violations": [Violation(
                "parse_error", "error", 0, "N/A",
                "Failed to parse XML file"
            ).to_dict()],
            "verdict": "FAIL",
            "checked_rules": [],
        }

    # Run all checkers
    all_violations = []
    checked_rules = []

    for rule_id, checker in [
        ("5.1", check_rule_5_1),
        ("5.4", check_rule_5_4),
        ("5.5", check_rule_5_5),
        ("5.7", check_rule_5_7_heuristic),
        ("5.12", check_rule_5_12),
        ("5.13", check_rule_5_13),
        ("5.14", check_rule_5_14),
    ]:
        try:
            violations = checker(root, line_map)
            all_violations.extend(violations)
            checked_rules.append(rule_id)
        except Exception as e:
            logger.error("Rule %s checker failed: %s", rule_id, e)

    # Determine verdict
    has_errors = any(v.severity == "error" for v in all_violations)
    verdict = "FAIL" if has_errors else "PASS"

    report = {
        "file": xml_path,
        "violations": [v.to_dict() for v in all_violations],
        "violation_count": len(all_violations),
        "error_count": sum(1 for v in all_violations if v.severity == "error"),
        "warning_count": sum(1 for v in all_violations if v.severity == "warning"),
        "verdict": verdict,
        "checked_rules": checked_rules,
    }

    logger.info(
        "Lint result for %s: %s (%d errors, %d warnings)",
        xml_path, verdict,
        report["error_count"], report["warning_count"],
    )

    return report


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python lint_layout.py <layout.xml> [--output lint_report.json]")
        sys.exit(1)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    xml_path = sys.argv[1]
    output_path = None

    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_path = sys.argv[idx + 1]

    report = lint_layout(xml_path)

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info("Lint report saved to %s", output_path)

    print(json.dumps(report, indent=2))
    sys.exit(0 if report["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
