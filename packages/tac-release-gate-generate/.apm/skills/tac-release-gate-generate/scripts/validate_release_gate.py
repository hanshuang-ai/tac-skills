#!/usr/bin/env python3
"""Validate the basic structure of a TAC release gate Markdown file."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED_PATTERNS = [
    ("title", r"^#\s+准出标准"),
    ("metadata", r"^##\s+元信息"),
    ("system level", r"^##\s+1\.\s+项目/系统级准出标准"),
    ("release level", r"^##\s+2\.\s+版本发布级准出标准"),
    ("feature level", r"^##\s+3\.\s+需求/功能级准出标准"),
    ("assumptions", r"^##\s+4\.\s+假设与待确认问题"),
]

STATUS_WORDS = {"TODO", "PASS", "FAIL", "BLOCKED", "N/A", "OPEN", "CLOSED"}


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_release_gate.py <04-准出标准.md>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"missing file: {path}", file=sys.stderr)
        return 2

    text = path.read_text(encoding="utf-8")
    missing = [name for name, pattern in REQUIRED_PATTERNS if not re.search(pattern, text, re.M)]
    ids = re.findall(r"\|\s*((?:SYS|REL|FEAT)-[HA]-\d{3})\s*\|", text)
    duplicate_ids = sorted({item for item in ids if ids.count(item) > 1})

    unknown_statuses = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if "|" not in line or re.match(r"^\s*\|?\s*-+", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[-1] and cells[-1].isupper() and cells[-1] not in STATUS_WORDS:
            unknown_statuses.append((line_no, cells[-1]))

    if missing or duplicate_ids or unknown_statuses:
        if missing:
            print("missing sections:")
            for name in missing:
                print(f"- {name}")
        if duplicate_ids:
            print("duplicate criterion IDs:")
            for item in duplicate_ids:
                print(f"- {item}")
        if unknown_statuses:
            print("unknown status values:")
            for line_no, status in unknown_statuses:
                print(f"- line {line_no}: {status}")
        return 1

    print(f"OK: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
