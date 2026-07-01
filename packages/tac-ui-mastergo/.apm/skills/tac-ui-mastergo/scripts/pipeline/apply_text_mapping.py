"""
Text Mapping Application Tool (Three-Step Architecture)

Replaces {{TEXT:<node_id>}} placeholders in XML layout files and Kotlin source
files with resolved text from text_mapping.json (produced by visual analysis
of the design screenshot in Phase E).

Usage:
    python apply_text_mapping.py <text_mapping.json> <layout_dir> [kotlin_dir]

Output:
    - Modified XML/Kotlin files with placeholders replaced
    - Replacement report printed to stdout
"""

import json
import logging
import os
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Pattern to match {{TEXT:node_id}} placeholders in XML and Kotlin files
PLACEHOLDER_PATTERN = re.compile(r"\{\{TEXT:([^}]+)\}\}")


def load_text_mapping(mapping_path: str) -> dict:
    """Load text_mapping.json and return a dict of placeholder -> resolved_text.
    
    Returns:
        Dict mapping placeholder strings like "{{TEXT:22:38587/63:27036}}"
        to their resolved text content.
    """
    with open(mapping_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    mapping = {}
    low_confidence = []

    for entry in data.get("mappings", []):
        placeholder = entry.get("placeholder", "")
        resolved = entry.get("resolved_text", "")
        confidence = entry.get("confidence", "high")

        if placeholder and resolved:
            mapping[placeholder] = resolved
            if confidence == "low":
                low_confidence.append(placeholder)

    if low_confidence:
        logger.warning(
            "%d mappings have low confidence and may need manual review:",
            len(low_confidence),
        )
        for p in low_confidence:
            logger.warning("  %s -> %s", p, mapping[p])

    unmapped = data.get("unmapped", [])
    if unmapped:
        logger.warning(
            "%d placeholders could not be mapped (see text_mapping.json 'unmapped'):",
            len(unmapped),
        )
        for entry in unmapped:
            logger.warning("  %s: %s", entry.get("placeholder"), entry.get("reason"))

    return mapping


def replace_in_file(file_path: Path, mapping: dict) -> int:
    """Replace all {{TEXT:xxx}} placeholders in a single file.
    
    Args:
        file_path: Path to the file to process.
        mapping: Dict of placeholder -> resolved text.
    
    Returns:
        Number of replacements made in this file.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    count = 0
    original = content

    for placeholder, text in mapping.items():
        if placeholder in content:
            # For XML files, escape special characters in text content
            if file_path.suffix == ".xml":
                escaped_text = _escape_xml(text)
            else:
                escaped_text = text

            content = content.replace(placeholder, escaped_text)
            occurrences = original.count(placeholder)
            count += occurrences

    if content != original:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    return count


def _escape_xml(text: str) -> str:
    """Escape special XML characters in text content."""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&apos;")
    return text


def find_remaining_placeholders(directory: Path, extensions: list) -> list:
    """Scan for any remaining {{TEXT:xxx}} placeholders after replacement.
    
    Returns:
        List of dicts with file, line_number, placeholder info.
    """
    remaining = []
    for ext in extensions:
        for fpath in directory.rglob(f"*{ext}"):
            with open(fpath, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    matches = PLACEHOLDER_PATTERN.findall(line)
                    for m in matches:
                        remaining.append({
                            "file": str(fpath),
                            "line": line_num,
                            "placeholder": f"{{{{TEXT:{m}}}}}",
                        })
    return remaining


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 3:
        print("Usage: python apply_text_mapping.py <text_mapping.json> <layout_dir> [kotlin_dir]")
        print()
        print("Arguments:")
        print("  text_mapping.json  Mapping file from Phase E visual analysis")
        print("  layout_dir         Directory containing XML layout files")
        print("  kotlin_dir         Optional directory containing Kotlin source files")
        sys.exit(1)

    mapping_path = sys.argv[1]
    layout_dir = Path(sys.argv[2])
    kotlin_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else None

    # Load mapping
    mapping = load_text_mapping(mapping_path)
    logger.info("Loaded %d text mappings from %s", len(mapping), mapping_path)

    if not mapping:
        logger.warning("No mappings loaded. Nothing to replace.")
        return

    # Process XML files
    total_replacements = 0
    files_modified = 0

    logger.info("Processing XML files in %s...", layout_dir)
    for xml_file in layout_dir.rglob("*.xml"):
        count = replace_in_file(xml_file, mapping)
        if count > 0:
            total_replacements += count
            files_modified += 1
            logger.info("  %s: %d replacements", xml_file.name, count)

    # Process Kotlin files (if provided)
    if kotlin_dir and kotlin_dir.exists():
        logger.info("Processing Kotlin files in %s...", kotlin_dir)
        for kt_file in kotlin_dir.rglob("*.kt"):
            count = replace_in_file(kt_file, mapping)
            if count > 0:
                total_replacements += count
                files_modified += 1
                logger.info("  %s: %d replacements", kt_file.name, count)

    # Check for remaining placeholders
    remaining = find_remaining_placeholders(layout_dir, [".xml"])
    if kotlin_dir and kotlin_dir.exists():
        remaining.extend(find_remaining_placeholders(kotlin_dir, [".kt"]))

    # Report
    logger.info("=" * 60)
    logger.info("TEXT REPLACEMENT SUMMARY:")
    logger.info("  Total replacements: %d", total_replacements)
    logger.info("  Files modified:     %d", files_modified)
    logger.info("  Remaining placeholders: %d", len(remaining))
    if remaining:
        logger.warning("  UNRESOLVED placeholders:")
        for r in remaining:
            logger.warning(
                "    %s:%d -> %s", 
                os.path.basename(r["file"]), r["line"], r["placeholder"]
            )
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
