# Mode B Renderer Workflow

Use this file only after entry routing selects Mode B.

## Context Loading Contract

Mode B may read:

- `<work_dir>/handoff_prompt.md`
- `<work_dir>/pipeline_result.json`
- `<work_dir>/user_decisions.json` if present
- `<work_dir>/handoff_facts.json`
- `<work_dir>/recursive_blueprint.json`
- `<work_dir>/render_plan.md` after it is generated in Mode B planning
- `<work_dir>/token_registry.json`
- `<work_dir>/colors_patch.xml`
- `<work_dir>/dimens_patch.xml`
- `<work_dir>/text_appearances_patch.xml`
- `prompts/render_plan.md`
- `prompts/layout_android_xml.md`
- `references/02_asset_processing.md`
- Mode B scripts: `pipeline/validate_handoff.py`, `query/dsl_query.py`, `query/query_semantic_mapping.py`, `pipeline/getdsl_to_file.py`, `pipeline/lint_layout.py`, `pipeline/extract_assets.py`, `pipeline/apply_text_mapping.py`, `query/query_widget_registry.py`

Mode B must not read:

- `<work_dir>/semantic_mapping.json` directly; use `scripts/query/query_semantic_mapping.py`
- `<work_dir>/mastergo_raw.json` directly; use `scripts/query/dsl_query.py`
- `references/widget_registry.snapshot.json` or library-specific registry snapshots directly; use `scripts/query/query_widget_registry.py`
- `references/01_data_acquisition.md`
- `references/03_blueprint_guide.md`
- `prompts/recursive_blueprint.md`
- `templates/mode_a_summary.md`
- Mode A analysis instructions or blueprint-generation prompts

## Goal

Render the already approved Mode A handoff into Android implementation artifacts. Do not reinterpret Mode A decisions.

## Preflight

1. Run:
   `python tac-skills/tac-ui-mastergo/scripts/pipeline/validate_handoff.py <work_dir>`
2. If result is `FAIL`, stop and report missing or invalid artifacts.
3. If result is `ALL PASS` or only minor warnings, continue.
4. Read `pipeline_result.json` for `file_context.fileId`.
5. Create `<work_dir>/dsl_query_cache/` if query outputs need to be saved for auditing.
6. Read `handoff_facts.json`, `recursive_blueprint.json`, and optional `user_decisions.json` if present. Do not read `semantic_mapping.json` directly; query required node IDs with `scripts/query/query_semantic_mapping.py`.
7. Do not read `mastergo_raw.json` directly and do not call chat/MCP getDsl for Mode B subtrees. Use bounded `scripts/query/dsl_query.py` queries against cached DSL files.
8. Merge token patches selectively into project resources, prioritizing existing project values.

## Phase B0: Render Planning Before Coding

1. Read `prompts/render_plan.md`.
2. Read `handoff_facts.json` first and treat it as the excerpt index/source of truth for confirmed scope, decisions, coordinate policy refs, module refs, layout reuse refs, edge-case refs, and unresolved refs.
3. Generate `<work_dir>/render_plan.md` as a concise execution plan immediately before coding. This is a Mode B planning artifact, not a Mode A handoff artifact.
4. Cover only:
   - User/workflow decisions referenced by `handoff_facts.json.confirmed_render_scope` and `decision_refs`
   - Layout reuse strategy referenced by `handoff_facts.json.layout_reuse_refs`
   - System chrome exclusions and coordinate normalization referenced by `handoff_facts.json.coordinate_policy_refs`
   - Special rendering edge cases referenced by `handoff_facts.json.edge_case_refs` and `unresolved_refs`
   - Coding task checklist with unchecked boxes before implementation starts
5. Before coding, verify every node ID, decision ID, coordinate offset, and source pointer mentioned in `render_plan.md` exists in `handoff_facts.json`, `recursive_blueprint.json`, or the referenced artifact.
6. Do not pause after writing `render_plan.md`; continue directly into layout generation unless the plan exposes a blocking contradiction in the Mode A handoff.

## Phase C: Layout Skeleton Generation

1. Read the newly generated `<work_dir>/render_plan.md`, then read `prompts/layout_android_xml.md`.
2. Process `recursive_blueprint.json` level by level.
3. For every rendered node, query only the needed bounded DSL slice:
   `python tac-skills/tac-ui-mastergo/scripts/query/dsl_query.py node <work_dir>/mastergo_raw.json --node-id <node.id> --depth 1 --max-children 20`
   Increase `--depth` only for the current component being generated, and keep `--max-children` explicit. Never request or paste the full raw DSL.
4. Use bounded DSL query output as the structural/style source of truth, and use bounded `scripts/query/query_semantic_mapping.py` output for semantic hints.
5. Apply user/script/workflow-default decisions exactly as recorded in `user_decisions.json` and/or already reflected in `recursive_blueprint.json`.
6. Exclude system chrome and normalize depth-0 renderable coordinates once, using `recursive_blueprint.json.coordinate_normalization`, each node's `coordinate_space`, and the machine-readable `bounds` fields. For root renderable children, use `bounds.normalized`; for descendants, use `bounds.parent_relative`. Do not infer left/right placement from prose notes.
7. Resolve list spacing only from `list_metrics_ref` entries that match `structural_hints.json.list_metrics[].container_id`, or from explicit `list_metrics_override` evidence.
8. Use placeholders for unresolved text and icons.
9. Record placeholders in `placeholder_manifest.json`.
10. For dynamic nodes, generate Adapter/data model/dummy data/wiring as required by the blueprint.
11. Run `lint_layout.py` and fix violations, max two iterations.

## Phase D: Icon And Bitmap Asset Resolution

1. Read `references/02_asset_processing.md`.
2. Run asset extraction:
   `python tac-skills/tac-ui-mastergo/scripts/pipeline/extract_assets.py extract <output_drawable_dir> <work_dir>/mastergo_raw.json --manifest <work_dir>/placeholder_manifest.json`
3. Prefer shared WT-library drawables for canonical icon names.
4. If component masters are missing, batch-fetch all missing components before rerunning extraction.
5. Replace icon placeholders:
   `python tac-skills/tac-ui-mastergo/scripts/pipeline/extract_assets.py replace <layout_dir> <work_dir>/placeholder_manifest.json`

## Phase E: Text Calibration

1. Check `<work_dir>/design_screenshot.png`.
2. If missing, tell the user accurate text calibration needs a screenshot and leave placeholders or use manual mapping.
3. If present, produce `text_mapping.json` by correlating screenshot text with placeholder coordinates.
4. Apply text mapping:
   `python tac-skills/tac-ui-mastergo/scripts/pipeline/apply_text_mapping.py <text_mapping.json> <layout_dir> [kotlin_dir]`

## Final Verification

- XML lint passes
- Build or targeted resource validation passes where feasible
- Placeholder manifest has no unexpected unresolved critical items
- Shared-library icon references resolve
- Generated fallback drawables exist
- Chrome exclusion and coordinate normalization match `recursive_blueprint.json`; no depth-0 renderable XML uses raw DSL `relativeX` / `relativeY` after top/left chrome is excluded
- Critical XML positions and sizes match `recursive_blueprint.json.bounds` rather than prose notes
