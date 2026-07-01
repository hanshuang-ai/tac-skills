---
name: tac-ui-mastergo
version: 0.4.8
description: >
  Converts MasterGo designs into pixel-perfect Android XML layouts using a
  relay-style separation between Mode A planning and Mode B rendering. Use when
  provided with a MasterGo URL, shortLink, fileId+layerId, or an existing work
  directory with blueprint artifacts.
---

# MasterGo Three-Step Pixel-Perfect UI Generation v2

This skill has two execution modes:

- **Mode A: Planner** -- fetch MasterGo DSL, run preprocessing, clarify facts, generate blueprint/render plan, and stop with a handoff directory.
- **Mode B: Renderer** -- consume an existing Mode A handoff directory and generate Android implementation artifacts.

## Mandatory Entry Routing

Determine the execution mode before reading any prompt, reference, template, or workflow file.

### Mode A: Planner

Trigger when the user provides:

- A MasterGo URL or shortLink, such as `https://uxd.tinnove.com.cn/goto/xxx`
- A `fileId` + `layerId`
- A request to analyze a design, generate a blueprint, or create a Mode A handoff

Action:

1. Read only `references/mode_a_workflow.md`.
2. Follow that workflow.
3. Stop after the Mode A handoff is valid.

### Mode B: Renderer

Trigger when the user provides:

- A work directory containing `recursive_blueprint.json`
- A request to render, generate code, continue from a blueprint, execute Phase C, or execute Mode B

Action:

1. Read only `references/mode_b_workflow.md`.
2. Follow that workflow.
3. Do not rerun Mode A analysis unless validation fails and the user asks to regenerate the handoff.

### Full Mode

Only run Mode A and Mode B in one session if the user explicitly asks for full end-to-end execution. Full mode is not recommended for complex designs because it mixes planning and rendering context.

## Context Isolation Rules

These rules are hard requirements.

### If Mode A Is Selected

Do not load:

- `references/mode_b_workflow.md`
- `references/02_asset_processing.md`
- `prompts/layout_android_xml.md`
- Mode B-only implementation details such as XML lint rules, asset replacement rules, Adapter generation rules, and text-application rules

Allowed Mode A files are listed in `references/mode_a_workflow.md`.

### If Mode B Is Selected

Do not load:

- `references/mode_a_workflow.md`
- `references/01_data_acquisition.md`
- `references/03_blueprint_guide.md`
- `prompts/recursive_blueprint.md`
- `prompts/render_plan.md`
- `templates/mode_a_summary.md`
- Mode A-only analysis and blueprint-generation instructions

Allowed Mode B files are listed in `references/mode_b_workflow.md`.

## Source-Of-Truth Rules

- DSL is the source of truth for exact dimensions, colors, typography, spacing, and effects.
- If the user provides a design screenshot, Mode A must use it before render-scope confirmation to identify the macro layout frame: overall visible modules, approximate positions, and roles such as left tab/sidebar, center list/content, lower banner, top toolbar, right panel, bottom navigation, or floating controls. Combine this screenshot evidence with DSL-derived nodes/bounds before asking which regions to implement. After the user confirms the scope, downstream DSL analysis and blueprint decomposition must be constrained to that confirmed screenshot+DSL/user scope plus required ancestor/coordinate context.
- For any intermediate artifact that has a query script, agents must not read/load/paste the artifact directly into chat/context. Access it only through the matching query script.
- `mastergo_raw.json` and full DSL payloads must be inspected only through bounded `scripts/query/dsl_query.py` queries against cached DSL files.
- `semantic_mapping.json` must be inspected only through `scripts/query/query_semantic_mapping.py` for specific node IDs.
- `widget_registry.snapshot.json` and library-specific widget registry snapshots must be inspected only through `scripts/query/query_widget_registry.py` for specific components, text styles, or color resources.
- This restriction applies to agent/context access. Purpose-built pipeline/query/validation scripts may receive these files as path arguments and parse them internally.
- Mode A blueprints must carry machine-readable DSL-derived bounds and exact list metric references; prose notes are not sufficient for layout geometry.
- DSL is not reliable for final designer-entered text or INSTANCE icon vector paths.
- Widget-matched nodes may keep widget default appearance, but layout geometry and sizing still come from DSL.
- Never guess values. Use `[UNRESOLVED: <reason>]` or explicit placeholders when data is missing.
- MasterGo px maps directly to Android dp unless a workflow file says otherwise.
- Top/bottom shell chrome and decorative shell-edge strips are excluded by default only when they match the workflow criteria; real page-owned navigation/toolbars remain renderable.

## Bundled Files

### Mode Workflows

| File | Use |
|:---|:---|
| `references/mode_a_workflow.md` | Mode A only |
| `references/mode_b_workflow.md` | Mode B only |

### Mode A Inputs

| File | Use |
|:---|:---|
| `references/01_data_acquisition.md` | DSL fetch and preprocessing guidance |
| `references/03_blueprint_guide.md` | Recursive blueprint guidance |
| `prompts/recursive_blueprint.md` | Blueprint JSON generation |
| `prompts/render_plan.md` | Render plan Markdown generation |
| `templates/mode_a_summary.md` | Chinese user-facing Mode A summary template |
| `templates/page_ui_spec.md` | Chinese page UI specification document template |

### Mode B Inputs

| File | Use |
|:---|:---|
| `prompts/layout_android_xml.md` | Android XML generation rules |
| `references/02_asset_processing.md` | Icon and bitmap asset processing |

### Shared Helpers

| File | Use |
|:---|:---|
| `references/04_dsl_schema.md` | DSL field reference; load only if needed |
| `references/05_widget_registry_query.md` | Widget registry query guide; load only if needed |
| `scripts/pipeline/getdsl_to_file.py` | Direct-to-disk DSL fetch only; never paste/read the full payload in chat |
| `scripts/query/dsl_query.py` | Bounded DSL node/children/find/ancestor query; use instead of reading raw DSL or fetching Mode B subtrees |
| `scripts/pipeline/pipeline.py` | Mode A preprocessing |
| `scripts/pipeline/validate_handoff.py` | Mode B preflight and Mode A handoff validation |
| `scripts/query/query_widget_registry.py` | Progressive widget-registry lookup |
| `scripts/query/query_semantic_mapping.py` | Query matching attributes and resolved widget/text details in semantic_mapping.json by node IDs |

## Default Output Boundary

- Mode A final answer should report the handoff directory, user/workflow decisions if any, validation status, and paths to `mode_a_summary.md`, `handoff_prompt.md`, `page_ui_spec.md`, and its copied destination `persistent-assets/design/_baseline/ui/page_ui_spec_xxxx页面.md`.
- Mode B final answer should report generated/modified Android artifacts, placeholder status, asset/text calibration status, and verification results.
