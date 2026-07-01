#!/usr/bin/env python3
"""
Batch validation runner for the repo-local tac-ui-mastergo skill.

This script reuses the existing tac-ui-mastergo acquisition and pipeline scripts,
then adds deterministic quality checks around semantic mapping output.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_PYTHON = (
    r"C:\Users\TINNOVE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
)
DEFAULT_WIDGET_ROOT = os.environ.get("WT_WIDGET_ROOT", r"D:\code\WT02_Widget")
REGISTRY_BASELINE = {
    "minWidgetCount": 74,
    "minTextStyleCount": 87,
    "minColorResourceCount": 358,
    "minRuntimeOnlyCount": 7,
    "requiredWidgets": [
        "WTSideBar",
        "WTRadioButton",
        "WTFloatSeekBar",
        "WTNavigationGroup",
        "WTItemWindow",
        "WTChoiceChips",
        "WTNavigationBar",
        "WTProgressBar",
        "WTTitleBar",
        "WTTopSlideBar",
        "WTSwitch",
    ],
    "requiredRuntimeOnlyWidgets": [
        "WTEmptyDialog",
        "WTPushDialog",
        "WTDatePickerDialog",
        "WTTimePickerDialog",
        "WTItemWindow",
        "WTSnackBar",
        "WTAutoBubble",
    ],
    "requiredVariantCounts": {
        "WTChoiceChips": 8,
        "WTNavigationBar": 5,
        "WTProgressBar": 5,
        "WTTitleBar": 2,
        "WTTopSlideBar": 2,
        "WTSwitch": 2,
    },
}


@dataclass
class LinkCase:
    label: str
    short_link: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate tac-ui-mastergo against one or more MasterGo short links."
    )
    parser.add_argument("output_root", help="Campaign output directory")
    parser.add_argument(
        "--short-link",
        action="append",
        default=[],
        help="MasterGo short link. Can be repeated.",
    )
    parser.add_argument(
        "--links-file",
        help="Optional file containing one short link per line, or label|url.",
    )
    parser.add_argument(
        "--python-exe",
        default=DEFAULT_PYTHON,
        help="Python runtime used to invoke existing tac-ui-mastergo scripts.",
    )
    parser.add_argument(
        "--widget-root",
        default=DEFAULT_WIDGET_ROOT,
        help="WT widget repo root passed through to the pipeline.",
    )
    parser.add_argument(
        "--library",
        default="wt",
        help="Registered tac-ui-mastergo library id passed through to the pipeline.",
    )
    parser.add_argument(
        "--reuse-existing",
        action="store_true",
        help="Skip fetching or pipeline steps when expected files already exist.",
    )
    return parser.parse_args()


def load_cases(short_links: list[str], links_file: str | None) -> list[LinkCase]:
    cases: list[LinkCase] = []
    for index, url in enumerate(short_links, start=1):
        cases.append(LinkCase(label=f"case-{index:02d}", short_link=url.strip()))

    if links_file:
        lines = Path(links_file).read_text(encoding="utf-8").splitlines()
        base = len(cases)
        for offset, line in enumerate(lines, start=1):
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            if "|" in raw:
                label, url = raw.split("|", 1)
                cases.append(LinkCase(label=label.strip(), short_link=url.strip()))
                continue
            parts = raw.split()
            if len(parts) == 1:
                cases.append(LinkCase(label=f"case-{base + offset:02d}", short_link=parts[0]))
            else:
                cases.append(LinkCase(label=" ".join(parts[:-1]), short_link=parts[-1]))

    if not cases:
        raise SystemExit("No short links provided. Use --short-link or --links-file.")
    return cases


def slugify(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-").lower()
    return text[:60] or "case"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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
    combined = []
    if process.stdout:
        combined.append(process.stdout)
    if process.stderr:
        combined.append(process.stderr)
    output = "\n".join(combined).strip()
    log_path.write_text(output, encoding="utf-8")
    return process.returncode, output


def flatten_nodes(nodes: Iterable[dict]) -> list[dict]:
    result: list[dict] = []

    def walk(node: dict) -> None:
        result.append(node)
        for child in node.get("children") or []:
            if isinstance(child, dict):
                walk(child)

    for node in nodes:
        if isinstance(node, dict):
            walk(node)
    return result


def extract_token_hits(styles: dict) -> Counter[str]:
    hits: Counter[str] = Counter()
    for entry in styles.values():
        if not isinstance(entry, dict):
            continue
        token = entry.get("token")
        if not token:
            continue
        tail = token.split("/")[-1]
        if tail.startswith("wt_") or tail.startswith("WTTextStyle"):
            hits[tail] += 1
    return hits


def ancestors(node_id: str) -> list[str]:
    parts = node_id.split("/")
    return ["/".join(parts[:i]) for i in range(len(parts) - 1, 0, -1)]


def analyze_registry(case_dir: Path, library: str = "") -> dict:
    registry_root = (
        Path(__file__).resolve().parent.parent.parent
        / "tac-ui-mastergo"
        / "references"
    )
    registry_path = registry_root / "widget_registry.snapshot.json"
    if library:
        library_registry_path = registry_root / "libraries" / library / "widget_registry.snapshot.json"
        if library_registry_path.exists():
            registry_path = library_registry_path
    if not registry_path.exists():
        registry_path = case_dir / "widget_registry.json"

    if not registry_path.exists():
        return {
            "present": False,
            "issueTypes": ["registry_missing"],
        }

    registry = load_json(registry_path)
    widgets = registry.get("widgets") or []
    text_styles = registry.get("textStyles") or []
    color_resources = registry.get("colorResources") or []
    simple_name_map = {
        widget.get("simpleName"): widget for widget in widgets if widget.get("simpleName")
    }
    runtime_only_names = sorted(
        widget.get("simpleName")
        for widget in widgets
        if widget.get("renderKind") == "runtime_only" and widget.get("simpleName")
    )

    missing_required_widgets = [
        name for name in REGISTRY_BASELINE["requiredWidgets"] if name not in simple_name_map
    ]
    missing_runtime_only_widgets = [
        name for name in REGISTRY_BASELINE["requiredRuntimeOnlyWidgets"] if name not in runtime_only_names
    ]

    variant_regressions = []
    for widget_name, min_variants in REGISTRY_BASELINE["requiredVariantCounts"].items():
        widget = simple_name_map.get(widget_name)
        actual = len(widget.get("variants") or []) if widget else 0
        if actual < min_variants:
            variant_regressions.append(
                {
                    "widget": widget_name,
                    "expectedMin": min_variants,
                    "actual": actual,
                }
            )

    issue_types: list[str] = []
    if len(widgets) < REGISTRY_BASELINE["minWidgetCount"]:
        issue_types.append("registry_widget_count_regression")
    if len(text_styles) < REGISTRY_BASELINE["minTextStyleCount"]:
        issue_types.append("registry_text_style_regression")
    if len(color_resources) < REGISTRY_BASELINE["minColorResourceCount"]:
        issue_types.append("registry_color_resource_regression")
    if len(runtime_only_names) < REGISTRY_BASELINE["minRuntimeOnlyCount"]:
        issue_types.append("registry_runtime_only_regression")
    if missing_required_widgets:
        issue_types.append("registry_required_widget_missing")
    if missing_runtime_only_widgets:
        issue_types.append("registry_runtime_only_widget_missing")
    if variant_regressions:
        issue_types.append("registry_variant_regression")

    return {
        "present": True,
        "widgetCount": len(widgets),
        "textStyleCount": len(text_styles),
        "colorResourceCount": len(color_resources),
        "runtimeOnlyCount": len(runtime_only_names),
        "runtimeOnlyWidgets": runtime_only_names,
        "missingRequiredWidgets": missing_required_widgets,
        "missingRuntimeOnlyWidgets": missing_runtime_only_widgets,
        "variantRegressions": variant_regressions,
        "issueTypes": issue_types,
    }


def analyze_case(case_dir: Path, library: str = "") -> dict:
    raw_payload = load_json(case_dir / "mastergo_raw.json")
    dsl = raw_payload.get("dsl", raw_payload)
    nodes = flatten_nodes(dsl.get("nodes") or [])
    styles = dsl.get("styles") or {}

    component_descriptions = Counter(
        str((node.get("componentInfo") or {}).get("description"))
        for node in nodes
        if (node.get("componentInfo") or {}).get("description")
    )

    component_description_nodes = [
        node.get("id")
        for node in nodes
        if (node.get("componentInfo") or {}).get("description")
    ]

    semantic_path = case_dir / "semantic_mapping.json"
    mappings = []
    if semantic_path.exists():
        semantic_payload = load_json(semantic_path)
        mappings = semantic_payload.get("nodes") or []

    resolved = [entry for entry in mappings if entry.get("resolvedWidget")]
    strong = [
        entry
        for entry in resolved
        if "componentInfo.description" in (entry.get("evidence") or [])
    ]
    weak = [
        entry
        for entry in resolved
        if "componentInfo.description" not in (entry.get("evidence") or [])
    ]

    resolved_by_id = {entry.get("nodeId"): entry for entry in resolved if entry.get("nodeId")}
    duplicate_descendants = []
    for entry in weak:
        node_id = entry.get("nodeId")
        widget = (entry.get("resolvedWidget") or {}).get("className")
        if not node_id or not widget:
            continue
        for ancestor_id in ancestors(node_id):
            ancestor_entry = resolved_by_id.get(ancestor_id)
            if not ancestor_entry:
                continue
            ancestor_widget = (ancestor_entry.get("resolvedWidget") or {}).get("className")
            if ancestor_widget == widget:
                duplicate_descendants.append(
                    {
                        "nodeId": node_id,
                        "ancestorNodeId": ancestor_id,
                        "className": widget,
                        "evidence": entry.get("evidence") or [],
                    }
                )
                break

    strong_node_ids = {entry.get("nodeId") for entry in strong if entry.get("nodeId")}
    unmapped_explicit_nodes = [
        node_id for node_id in component_description_nodes if node_id not in strong_node_ids
    ]

    registry_summary = analyze_registry(case_dir, library)
    issue_types: list[str] = list(registry_summary.get("issueTypes") or [])
    if weak:
        issue_types.append("weak_widget_match")
    if duplicate_descendants:
        issue_types.append("descendant_duplicate_match")
    if unmapped_explicit_nodes:
        issue_types.append("explicit_component_not_mapped")

    token_hits = extract_token_hits(styles)
    resolved_widget_counts = Counter(
        (entry.get("resolvedWidget") or {}).get("className")
        for entry in resolved
        if (entry.get("resolvedWidget") or {}).get("className")
    )

    result = "PASS"
    if issue_types:
        result = "NEEDS_ITERATION"

    return {
        "result": result,
        "componentDescriptionCounts": dict(component_descriptions),
        "explicitComponentNodeCount": len(component_description_nodes),
        "resolvedWidgetCounts": dict(resolved_widget_counts),
        "strongMatchCount": len(strong),
        "weakMatchCount": len(weak),
        "duplicateDescendantMatches": duplicate_descendants,
        "unmappedExplicitNodes": unmapped_explicit_nodes,
        "wtTokenHits": dict(token_hits),
        "registrySummary": registry_summary,
        "issueTypes": sorted(set(issue_types)),
        "weakMatches": [
            {
                "nodeId": entry.get("nodeId"),
                "nodeType": entry.get("nodeType"),
                "evidence": entry.get("evidence") or [],
                "className": (entry.get("resolvedWidget") or {}).get("className"),
                "renderKind": (entry.get("resolvedWidget") or {}).get("renderKind", "xml_view"),
            }
            for entry in weak
        ],
    }


def build_iteration_hints(issue_counts: Counter[str]) -> list[str]:
    hints: list[str] = []
    if issue_counts.get("registry_missing"):
        hints.append(
            "Inspect pipeline.py and build_widget_registry.py first; validation needs widget_registry.json to evaluate semantic coverage correctly."
        )
    if issue_counts.get("registry_widget_count_regression") or issue_counts.get("registry_required_widget_missing"):
        hints.append(
            "Inspect build_widget_registry.py filters and manual_widgets coverage; widget registry lost required public controls."
        )
    if issue_counts.get("registry_text_style_regression"):
        hints.append(
            "Inspect build_widget_registry.py text-style collection; component-level text styles should not collapse back to WTTextStyle-only coverage."
        )
    if issue_counts.get("registry_color_resource_regression"):
        hints.append(
            "Inspect build_widget_registry.py color filtering; colorResources should contain pure color entries from colors.xml, not lose coverage."
        )
    if issue_counts.get("registry_runtime_only_regression") or issue_counts.get("registry_runtime_only_widget_missing"):
        hints.append(
            "Sync widget_semantic_rules.json manual runtime-only widgets with extract_semantic_mapping.py expectations."
        )
    if issue_counts.get("registry_variant_regression"):
        hints.append(
            "Inspect widget_semantic_rules.json variant aliases/style maps for high-frequency widgets like chips, navigation, progress, title bar, top slide bar, and switch."
        )
    if issue_counts.get("weak_widget_match"):
        hints.append(
            "Lower node.name authority in extract_semantic_mapping.py and downgrade node.name-only hits to candidate output."
        )
    if issue_counts.get("descendant_duplicate_match"):
        hints.append(
            "Add subtree de-duplication so child layers inside a confirmed widget do not resolve to the same widget class again."
        )
    if issue_counts.get("explicit_component_not_mapped"):
        hints.append(
            "Inspect widget_registry aliases and variant rules before changing prompts; explicit componentInfo.description nodes should map first."
        )
    if issue_counts.get("fetch_failed"):
        hints.append(
            "Rerun failed fetches with escalated network permissions instead of changing Python dependencies."
        )
    if issue_counts.get("pipeline_failed"):
        hints.append(
            "Fix the smallest failing pipeline script under tac-ui-mastergo/scripts before expanding prompt logic."
        )
    return hints


def write_case_report(case_dir: Path, case_name: str, link: str, fetch_status: str, pipeline_status: str, summary: dict) -> None:
    component_description_counts = summary.get("componentDescriptionCounts", {})
    resolved_widget_counts = summary.get("resolvedWidgetCounts", {})
    explicit_component_node_count = summary.get("explicitComponentNodeCount", 0)
    strong_match_count = summary.get("strongMatchCount", 0)
    weak_match_count = summary.get("weakMatchCount", 0)
    duplicate_descendants = summary.get("duplicateDescendantMatches", [])
    issue_types = summary.get("issueTypes", [])
    weak_matches = summary.get("weakMatches", [])
    registry_summary = summary.get("registrySummary", {})

    lines = [
        f"# {case_name}",
        "",
        "## Input",
        "",
        f"- short link: `{link}`",
        f"- fetch: `{fetch_status}`",
        f"- pipeline: `{pipeline_status}`",
        f"- result: `{summary['result']}`",
        "",
        "## Explicit Component Descriptions",
        "",
    ]

    if component_description_counts:
        for name, count in sorted(component_description_counts.items()):
            lines.append(f"- `{name}`: `{count}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Resolved Widgets", ""])
    if resolved_widget_counts:
        for name, count in sorted(resolved_widget_counts.items()):
            lines.append(f"- `{name}`: `{count}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Widget Registry", ""])
    if registry_summary.get("present"):
        lines.append(f"- widget count: `{registry_summary.get('widgetCount', 0)}`")
        lines.append(f"- text styles: `{registry_summary.get('textStyleCount', 0)}`")
        lines.append(f"- color resources: `{registry_summary.get('colorResourceCount', 0)}`")
        lines.append(f"- runtime-only widgets: `{registry_summary.get('runtimeOnlyCount', 0)}`")
        if registry_summary.get("missingRequiredWidgets"):
            lines.append(
                "- missing required widgets: "
                + ", ".join(f"`{name}`" for name in registry_summary["missingRequiredWidgets"])
            )
        if registry_summary.get("missingRuntimeOnlyWidgets"):
            lines.append(
                "- missing runtime-only widgets: "
                + ", ".join(f"`{name}`" for name in registry_summary["missingRuntimeOnlyWidgets"])
            )
        if registry_summary.get("variantRegressions"):
            for item in registry_summary["variantRegressions"]:
                lines.append(
                    f"- variant regression: `{item['widget']}` expected>={item['expectedMin']} actual=`{item['actual']}`"
                )
    else:
        lines.append("- widget_registry.json missing")

    lines.extend(
        [
            "",
            "## Quality Signals",
            "",
            f"- explicit component nodes: `{explicit_component_node_count}`",
            f"- strong matches: `{strong_match_count}`",
            f"- weak matches: `{weak_match_count}`",
            f"- duplicate descendant matches: `{len(duplicate_descendants)}`",
            "",
            "## Issue Types",
            "",
        ]
    )
    if issue_types:
        for issue in issue_types:
            lines.append(f"- `{issue}`")
    else:
        lines.append("- none")

    if weak_matches:
        lines.extend(["", "## Weak Matches", ""])
        for item in weak_matches[:10]:
            lines.append(
                f"- `{item['nodeId']}` -> `{item['className']}` ({item['renderKind']}) via `{', '.join(item['evidence'])}`"
            )

    if duplicate_descendants:
        lines.extend(["", "## Duplicate Descendant Matches", ""])
        for item in duplicate_descendants[:10]:
            lines.append(
                f"- `{item['nodeId']}` duplicates `{item['ancestorNodeId']}` as `{item['className']}`"
            )

    if summary.get("fetchOutputTail"):
        lines.extend(["", "## Fetch Output Tail", "", "```text", summary["fetchOutputTail"], "```"])

    if summary.get("pipelineOutputTail"):
        lines.extend(["", "## Pipeline Output Tail", "", "```text", summary["pipelineOutputTail"], "```"])

    case_report = "\n".join(lines) + "\n"
    (case_dir / "case_report.md").write_text(case_report, encoding="utf-8")


def main() -> int:
    args = parse_args()
    output_root = Path(args.output_root).resolve()
    cases_dir = output_root / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)

    cases = load_cases(args.short_link, args.links_file)
    campaign_rows = []
    issue_counts: Counter[str] = Counter()

    repo_root = Path.cwd()
    getdsl_script = repo_root / ".agents" / "skills" / "tac-ui-mastergo" / "scripts" / "getdsl_to_file.py"
    pipeline_script = repo_root / ".agents" / "skills" / "tac-ui-mastergo" / "scripts" / "pipeline.py"

    for index, case in enumerate(cases, start=1):
        case_name = f"{index:02d}-{slugify(case.label)}"
        case_dir = cases_dir / case_name
        case_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            case_dir / "case_input.json",
            {"label": case.label, "shortLink": case.short_link, "caseName": case_name},
        )

        raw_path = case_dir / "mastergo_raw.json"
        fetch_log = case_dir / "fetch.log"
        pipeline_log = case_dir / "pipeline.log"
        fetch_status = "SKIPPED"
        pipeline_status = "SKIPPED"

        if not (args.reuse_existing and raw_path.exists()):
            fetch_cmd = [
                args.python_exe,
                str(getdsl_script),
                str(raw_path),
                "--short-link",
                case.short_link,
            ]
            fetch_rc, fetch_output = run_command(fetch_cmd, repo_root, fetch_log)
            fetch_status = "SUCCESS" if fetch_rc == 0 else "FAILED"
        else:
            fetch_output = "reuse-existing mastergo_raw.json"
            fetch_log.write_text(fetch_output, encoding="utf-8")
            fetch_status = "SUCCESS"

        if fetch_status == "SUCCESS":
            semantic_path = case_dir / "semantic_mapping.json"
            if not (args.reuse_existing and semantic_path.exists()):
                pipeline_cmd = [
                    args.python_exe,
                    str(pipeline_script),
                    str(raw_path),
                    str(case_dir),
                    str(case_dir / "res"),
                    "--short-link",
                    case.short_link,
                    "--library",
                    args.library,
                ]
                env = os.environ.copy()
                env["WT_WIDGET_ROOT"] = args.widget_root
                process = subprocess.run(
                    pipeline_cmd,
                    cwd=str(repo_root),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    shell=False,
                    env=env,
                )
                combined = []
                if process.stdout:
                    combined.append(process.stdout)
                if process.stderr:
                    combined.append(process.stderr)
                pipeline_output = "\n".join(combined).strip()
                pipeline_log.write_text(pipeline_output, encoding="utf-8")
                pipeline_status = "SUCCESS" if process.returncode == 0 else "FAILED"
            else:
                pipeline_output = "reuse-existing semantic_mapping.json"
                pipeline_log.write_text(pipeline_output, encoding="utf-8")
                pipeline_status = "SUCCESS"
        else:
            pipeline_output = ""
            pipeline_log.write_text("pipeline skipped because fetch failed", encoding="utf-8")

        if fetch_status != "SUCCESS":
            summary = {
                "result": "BLOCKED",
                "issueTypes": ["fetch_failed"],
                "fetchOutputTail": fetch_output[-1000:],
            }
            issue_counts.update(summary["issueTypes"])
        elif pipeline_status != "SUCCESS":
            summary = {
                "result": "BLOCKED",
                "issueTypes": ["pipeline_failed"],
                "pipelineOutputTail": pipeline_output[-1000:],
            }
            issue_counts.update(summary["issueTypes"])
        else:
            summary = analyze_case(case_dir, args.library)
            issue_counts.update(summary["issueTypes"])

        write_json(case_dir / "case_summary.json", summary)
        write_case_report(case_dir, case_name, case.short_link, fetch_status, pipeline_status, summary)

        campaign_rows.append(
            {
                "caseName": case_name,
                "label": case.label,
                "shortLink": case.short_link,
                "fetchStatus": fetch_status,
                "pipelineStatus": pipeline_status,
                "result": summary["result"],
                "issueTypes": summary["issueTypes"],
            }
        )

    result_counts = Counter(row["result"] for row in campaign_rows)
    campaign_summary = {
        "campaignDir": str(output_root),
        "pythonExe": args.python_exe,
        "widgetRoot": args.widget_root,
        "library": args.library,
        "caseCount": len(campaign_rows),
        "resultCounts": dict(result_counts),
        "issueCounts": dict(issue_counts),
        "cases": campaign_rows,
        "iterationHints": build_iteration_hints(issue_counts),
    }
    write_json(output_root / "campaign_summary.json", campaign_summary)

    summary_lines = [
        "# Mastergogogo Validation Campaign",
        "",
        f"- campaign dir: `{output_root}`",
        f"- case count: `{campaign_summary['caseCount']}`",
        "",
        "## Result Counts",
        "",
    ]
    for name, count in sorted(result_counts.items()):
        summary_lines.append(f"- `{name}`: `{count}`")

    summary_lines.extend(["", "## Cases", ""])
    for row in campaign_rows:
        issues = ", ".join(row["issueTypes"]) if row["issueTypes"] else "none"
        summary_lines.append(
            f"- `{row['caseName']}` -> `{row['result']}`; fetch=`{row['fetchStatus']}`; pipeline=`{row['pipelineStatus']}`; issues=`{issues}`"
        )

    summary_lines.extend(["", "## Iteration Hints", ""])
    hints = campaign_summary["iterationHints"] or ["No repeated issues detected."]
    for hint in hints:
        summary_lines.append(f"- {hint}")

    summary_lines.extend(["", "## Registry Baseline", ""])
    summary_lines.append(f"- min widgets: `{REGISTRY_BASELINE['minWidgetCount']}`")
    summary_lines.append(f"- min text styles: `{REGISTRY_BASELINE['minTextStyleCount']}`")
    summary_lines.append(f"- min color resources: `{REGISTRY_BASELINE['minColorResourceCount']}`")
    summary_lines.append(f"- min runtime-only widgets: `{REGISTRY_BASELINE['minRuntimeOnlyCount']}`")

    (output_root / "campaign_summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    backlog_lines = ["# Iteration Backlog", ""]
    if hints:
        for index, hint in enumerate(hints, start=1):
            backlog_lines.append(f"{index}. {hint}")
    else:
        backlog_lines.append("1. No repeated issues detected.")
    (output_root / "iteration_backlog.md").write_text("\n".join(backlog_lines) + "\n", encoding="utf-8")

    print(json.dumps(campaign_summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
