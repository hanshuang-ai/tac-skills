#!/usr/bin/env python3
"""
Deterministic regression check for icon placeholder replacement.

This validates that the tac-ui-mastergo icon pipeline:
1. canonicalizes icon names like `All/ic_all_account` -> `ic_all_account`
2. prefers shared widget-library drawables over local extraction
3. replaces placeholder drawables in generated XML layouts correctly
4. keeps the prompt and skill contract aligned with that behavior
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_PYTHON = (
    r"C:\Users\TINNOVE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local icon-placeholder regression case.")
    parser.add_argument("output_dir", help="Directory to write regression outputs")
    parser.add_argument("--python-exe", default=DEFAULT_PYTHON, help="Python runtime used for tac-ui-mastergo scripts.")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def run_command(command: list[str], cwd: Path, log_path: Path) -> tuple[int, str]:
    process = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    output = "\n".join(part for part in (process.stdout, process.stderr) if part).strip()
    log_path.write_text(output, encoding="utf-8")
    return process.returncode, output


def assert_equal(actual, expected, label: str, failures: list[str]) -> None:
    if actual != expected:
        failures.append(f"{label}: expected `{expected}` got `{actual}`")


def assert_contains(haystack: str, needle: str, label: str, failures: list[str]) -> None:
    if needle not in haystack:
        failures.append(f"{label}: missing `{needle}`")


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd().resolve()
    output_dir = Path(args.output_dir).resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    skill_root = repo_root / ".agents" / "skills" / "tac-ui-mastergo"
    test_root = repo_root / ".agents" / "skills" / "tac-ui-mastergo-test"
    case_spec = load_json(test_root / "references" / "icon_placeholder_regression_case.json")

    raw_dsl_path = repo_root / case_spec["rawDslPath"]
    skill_path = repo_root / case_spec["skillPath"]
    prompt_path = repo_root / case_spec["promptPath"]
    asset_guide_path = repo_root / case_spec["assetGuidePath"]
    sample_icon = case_spec["sampleIcon"]

    layout_dir = output_dir / "layout"
    drawable_dir = output_dir / "drawable"
    layout_dir.mkdir(parents=True, exist_ok=True)
    drawable_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = output_dir / "placeholder_manifest.json"
    sample_layout_path = layout_dir / "sample_icon.xml"
    extract_log = output_dir / "extract_assets.log"
    replace_log = output_dir / "replace_assets.log"

    write_json(
        manifest_path,
        {
            "icon_placeholders": [
                {
                    "node_id": sample_icon["nodeId"],
                    "component_id": sample_icon["componentId"],
                    "placeholder": sample_icon["placeholder"],
                }
            ]
        },
    )
    sample_layout_path.write_text(
        "\n".join(
            [
                '<?xml version="1.0" encoding="utf-8"?>',
                '<ImageView xmlns:android="http://schemas.android.com/apk/res/android"',
                '    android:layout_width="56dp"',
                '    android:layout_height="56dp"',
                f'    android:src="{sample_icon["placeholder"]}" />',
                "",
            ]
        ),
        encoding="utf-8",
    )

    extract_cmd = [
        args.python_exe,
        str(skill_root / "scripts" / "extract_assets.py"),
        "extract",
        str(drawable_dir),
        str(raw_dsl_path),
        "--manifest",
        str(manifest_path),
    ]
    replace_cmd = [
        args.python_exe,
        str(skill_root / "scripts" / "extract_assets.py"),
        "replace",
        str(layout_dir),
        str(manifest_path),
    ]

    extract_rc, extract_output = run_command(extract_cmd, repo_root, extract_log)
    replace_rc, replace_output = run_command(replace_cmd, repo_root, replace_log)

    failures: list[str] = []
    if extract_rc != 0:
        failures.append("extract_assets.py extract failed")
    if replace_rc != 0:
        failures.append("extract_assets.py replace failed")

    layout_content = sample_layout_path.read_text(encoding="utf-8")
    assert_contains(layout_content, sample_icon["expectedDrawable"], "layout replacement", failures)

    unexpected_generated = drawable_dir / "ic_all_account.xml"
    if unexpected_generated.exists():
        failures.append("shared-library icon unexpectedly generated as a local fallback xml")

    missing_components_path = output_dir / "missing_components.json"
    if missing_components_path.exists():
        missing_data = load_json(missing_components_path)
        if missing_data.get("total_missing"):
            failures.append("shared-library icon unexpectedly reported as a missing component")

    assert_contains(extract_output, "shared: ic_all_account", "extract log shared icon", failures)
    assert_contains(extract_output, "Shared library icons:", "extract log summary", failures)

    raw_dsl_text = raw_dsl_path.read_text(encoding="utf-8")
    assert_contains(raw_dsl_text, sample_icon["name"], "raw DSL sample icon name", failures)

    skill_text = skill_path.read_text(encoding="utf-8")
    prompt_text = prompt_path.read_text(encoding="utf-8")
    asset_guide_text = asset_guide_path.read_text(encoding="utf-8")

    for snippet in case_spec.get("requiredSkillSnippets", []):
        assert_contains(skill_text, snippet, "skill contract", failures)
    for snippet in case_spec.get("requiredPromptSnippets", []):
        assert_contains(prompt_text, snippet, "prompt contract", failures)
    for snippet in case_spec.get("requiredAssetGuideSnippets", []):
        assert_contains(asset_guide_text, snippet, "asset guide contract", failures)

    result = {
        "case": case_spec["name"],
        "result": "PASS" if not failures else "FAIL",
        "sampleIcon": sample_icon,
        "layoutResult": {
            "sampleLayout": str(sample_layout_path),
            "expectedDrawable": sample_icon["expectedDrawable"],
            "content": layout_content,
        },
        "drawableOutput": {
            "directory": str(drawable_dir),
            "generatedFiles": sorted(path.name for path in drawable_dir.iterdir() if path.is_file()),
        },
        "logs": {
            "extract": str(extract_log),
            "replace": str(replace_log),
        },
        "commandStatus": {
            "extract": extract_rc,
            "replace": replace_rc,
        },
        "commandOutputTail": {
            "extract": extract_output[-1200:],
            "replace": replace_output[-1200:],
        },
        "failures": failures,
    }

    write_json(output_dir / "regression_summary.json", result)

    lines = [
        "# Icon Placeholder Regression",
        "",
        f"- case: `{case_spec['name']}`",
        f"- result: `{result['result']}`",
        f"- sample icon: `{sample_icon['name']}`",
        f"- expected drawable: `{sample_icon['expectedDrawable']}`",
        f"- extract log: `{extract_log}`",
        f"- replace log: `{replace_log}`",
        "",
        "## Replacement Check",
        "",
        f"- layout file: `{sample_layout_path}`",
        f"- final drawable reference present: `{sample_icon['expectedDrawable'] in layout_content}`",
        "",
        "## Drawable Output",
        "",
    ]

    generated_files = result["drawableOutput"]["generatedFiles"]
    if generated_files:
        for filename in generated_files:
            lines.append(f"- `{filename}`")
    else:
        lines.append("- no local fallback drawables generated for the sample icon")

    lines.extend(["", "## Failures", ""])
    if failures:
        for failure in failures:
            lines.append(f"- {failure}")
    else:
        lines.append("- none")

    (output_dir / "regression_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(result["result"])
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
