#!/usr/bin/env python3
"""
Deterministic regression check for text-style standardization.

This reuses a checked-in MasterGo DSL snapshot and validates:
1. widget_registry.json carries normalized text-style metadata
2. semantic_mapping.json carries styleRef / ownership / conflicts
3. layout_android_xml.md still contains the required prompt contract
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


DEFAULT_PYTHON = (
    r"C:\Users\TINNOVE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
)
DEFAULT_WIDGET_ROOT = r"D:\code\WT02_Widget"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local style-standardization regression case.")
    parser.add_argument("output_dir", help="Directory to write regression outputs")
    parser.add_argument("--python-exe", default=DEFAULT_PYTHON, help="Python runtime used for tac-ui-mastergo scripts.")
    parser.add_argument("--widget-root", default=DEFAULT_WIDGET_ROOT, help="WT widget repo root.")
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
    output_dir.mkdir(parents=True, exist_ok=True)

    skill_root = repo_root / ".agents" / "skills" / "tac-ui-mastergo"
    test_root = repo_root / ".agents" / "skills" / "tac-ui-mastergo-test"
    case_spec = load_json(test_root / "references" / "style_standardization_regression_case.json")

    raw_dsl_path = repo_root / case_spec["rawDslPath"]
    prompt_path = repo_root / case_spec["promptPath"]
    widget_registry_path = output_dir / "widget_registry.json"
    semantic_mapping_path = output_dir / "semantic_mapping.json"

    build_registry_log = output_dir / "build_widget_registry.log"
    semantic_mapping_log = output_dir / "extract_semantic_mapping.log"

    registry_cmd = [
        args.python_exe,
        str(skill_root / "scripts" / "build_widget_registry.py"),
        str(widget_registry_path),
        "--widget-root",
        args.widget_root,
    ]
    registry_rc, registry_output = run_command(registry_cmd, repo_root, build_registry_log)

    semantic_cmd = [
        args.python_exe,
        str(skill_root / "scripts" / "extract_semantic_mapping.py"),
        str(raw_dsl_path),
        str(widget_registry_path),
        str(semantic_mapping_path),
    ]
    semantic_rc, semantic_output = run_command(semantic_cmd, repo_root, semantic_mapping_log)

    failures: list[str] = []
    if registry_rc != 0:
        failures.append("build_widget_registry.py failed")
    if semantic_rc != 0:
        failures.append("extract_semantic_mapping.py failed")

    registry_summary = {}
    semantic_summary = {}
    prompt_summary = {}

    if registry_rc == 0 and widget_registry_path.exists():
        registry = load_json(widget_registry_path)
        text_styles = {item["name"]: item for item in registry.get("textStyles", []) if item.get("name")}
        checked_styles = []
        for expected in case_spec.get("requiredTextStyles", []):
            name = expected["name"]
            actual = text_styles.get(name)
            if not actual:
                failures.append(f"required text style missing from registry: `{name}`")
                continue
            assert_equal(actual.get("styleRef"), expected["styleRef"], f"{name}.styleRef", failures)
            assert_equal(actual.get("family"), expected["family"], f"{name}.family", failures)
            assert_equal(actual.get("variant"), expected["variant"], f"{name}.variant", failures)
            assert_equal(actual.get("weight"), expected["weight"], f"{name}.weight", failures)
            checked_styles.append(
                {
                    "name": name,
                    "styleRef": actual.get("styleRef"),
                    "family": actual.get("family"),
                    "variant": actual.get("variant"),
                    "weight": actual.get("weight"),
                }
            )
        registry_summary = {
            "textStyleCount": len(registry.get("textStyles", [])),
            "checkedStyles": checked_styles,
        }

    if semantic_rc == 0 and semantic_mapping_path.exists():
        semantic_mapping = load_json(semantic_mapping_path)
        node_map = {item.get("nodeId"): item for item in semantic_mapping.get("nodes", []) if item.get("nodeId")}
        checked_nodes = []
        for expected in case_spec.get("expectedTextNodes", []):
            node_id = expected["nodeId"]
            entry = node_map.get(node_id)
            if not entry:
                failures.append(f"semantic mapping missing node `{node_id}`")
                continue
            text = entry.get("text") or {}
            ownership = text.get("ownership") or {}
            conflicts = text.get("conflicts") or []
            assert_equal(text.get("styleRef"), expected["styleRef"], f"{node_id}.text.styleRef", failures)
            assert_equal(text.get("styleFamily"), expected["styleFamily"], f"{node_id}.text.styleFamily", failures)
            assert_equal(text.get("styleVariant"), expected["styleVariant"], f"{node_id}.text.styleVariant", failures)
            assert_equal(ownership.get("kind"), expected["ownershipKind"], f"{node_id}.text.ownership.kind", failures)
            if expected.get("colorValue"):
                assert_equal(text.get("colorValue"), expected["colorValue"], f"{node_id}.text.colorValue", failures)
            if expected.get("colorToken"):
                assert_equal(text.get("colorToken"), expected["colorToken"], f"{node_id}.text.colorToken", failures)
            if expected.get("ownershipOwnerWidget"):
                assert_equal(
                    ownership.get("ownerWidget"),
                    expected["ownershipOwnerWidget"],
                    f"{node_id}.text.ownership.ownerWidget",
                    failures,
                )
            conflict_blob = "\n".join(conflicts)
            for snippet in expected.get("conflictsContain", []):
                assert_contains(conflict_blob, snippet, f"{node_id}.text.conflicts", failures)
            checked_nodes.append(
                {
                    "nodeId": node_id,
                    "styleRef": text.get("styleRef"),
                    "styleFamily": text.get("styleFamily"),
                    "styleVariant": text.get("styleVariant"),
                    "colorValue": text.get("colorValue"),
                    "colorToken": text.get("colorToken"),
                    "ownership": ownership,
                    "conflicts": conflicts,
                }
            )
        semantic_summary = {
            "nodeCount": semantic_mapping.get("meta", {}).get("nodeCount", 0),
            "checkedNodes": checked_nodes,
        }

    prompt_text = prompt_path.read_text(encoding="utf-8")
    missing_prompt_snippets = []
    for snippet in case_spec.get("requiredPromptSnippets", []):
        if snippet not in prompt_text:
            missing_prompt_snippets.append(snippet)
            failures.append(f"prompt missing required snippet `{snippet}`")
    prompt_summary = {
        "promptPath": str(prompt_path),
        "checkedSnippets": case_spec.get("requiredPromptSnippets", []),
        "missingSnippets": missing_prompt_snippets,
    }

    result = {
        "case": case_spec["name"],
        "result": "PASS" if not failures else "FAIL",
        "registry": registry_summary,
        "semanticMapping": semantic_summary,
        "prompt": prompt_summary,
        "failures": failures,
        "logs": {
            "buildWidgetRegistry": str(build_registry_log),
            "extractSemanticMapping": str(semantic_mapping_log),
        },
        "commandStatus": {
            "buildWidgetRegistry": registry_rc,
            "extractSemanticMapping": semantic_rc,
        },
        "commandOutputTail": {
            "buildWidgetRegistry": registry_output[-800:],
            "extractSemanticMapping": semantic_output[-800:],
        },
    }

    write_json(output_dir / "regression_summary.json", result)

    lines = [
        "# Style Standardization Regression",
        "",
        f"- case: `{case_spec['name']}`",
        f"- result: `{result['result']}`",
        f"- widget registry log: `{build_registry_log}`",
        f"- semantic mapping log: `{semantic_mapping_log}`",
        "",
        "## Registry Checks",
        "",
    ]
    if registry_summary.get("checkedStyles"):
        for item in registry_summary["checkedStyles"]:
            lines.append(
                f"- `{item['name']}` -> `{item['styleRef']}` | family=`{item['family']}` | variant=`{item['variant']}` | weight=`{item['weight']}`"
            )
    else:
        lines.append("- no registry checks passed")

    lines.extend(["", "## Semantic Mapping Checks", ""])
    if semantic_summary.get("checkedNodes"):
        for item in semantic_summary["checkedNodes"]:
            lines.append(
                f"- `{item['nodeId']}` -> `{item['styleRef']}` | ownership=`{item['ownership'].get('kind')}`"
            )
            for conflict in item.get("conflicts", []):
                lines.append(f"  conflict: `{conflict}`")
    else:
        lines.append("- no semantic mapping checks passed")

    lines.extend(["", "## Prompt Checks", ""])
    if missing_prompt_snippets:
        for snippet in missing_prompt_snippets:
            lines.append(f"- missing: `{snippet}`")
    else:
        lines.append("- all required prompt snippets present")

    lines.extend(["", "## Failures", ""])
    if failures:
        for failure in failures:
            lines.append(f"- {failure}")
    else:
        lines.append("- none")

    (output_dir / "regression_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
