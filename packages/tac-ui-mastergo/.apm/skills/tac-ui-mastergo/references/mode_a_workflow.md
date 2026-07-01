# Mode A Planner Workflow

Use this file only after entry routing selects Mode A.

## Context Loading Contract

Mode A may read:

- `references/01_data_acquisition.md`
- `references/03_blueprint_guide.md`
- `prompts/recursive_blueprint.md`
- `prompts/handoff_facts.md`
- `templates/handoff_prompt.md`
- `templates/page_ui_spec.md` (only when the user opts to generate the optional page UI spec)
- Mode A scripts: `pipeline/getdsl_to_file.py`, `query/dsl_query.py`, `query/query_semantic_mapping.py`, `query/query_widget_registry.py`, `pipeline/pipeline.py`, `pipeline/extract_skeleton.py`, `pipeline/extract_tokens.py`, `pipeline/extract_semantic_mapping.py`, `pipeline/analyze_structure.py`

Mode A must not read:

- `<work_dir>/mastergo_raw.json` directly; use `scripts/query/dsl_query.py`
- `<work_dir>/semantic_mapping.json` directly; use `scripts/query/query_semantic_mapping.py`
- `references/widget_registry.snapshot.json` or library-specific registry snapshots directly; use `scripts/query/query_widget_registry.py`
- `references/02_asset_processing.md`
- `prompts/layout_android_xml.md`
- Mode B generation details, XML lint rules, asset replacement rules, or text-application rules

## Goal

Produce a complete handoff directory for later rendering. Stop after the handoff is valid. Do not generate Android layout/code in Mode A.

## Phase A: Data Acquisition

1. Read `references/01_data_acquisition.md`.
2. Fetch raw DSL to disk only with:
   `python tac-skills/tac-ui-mastergo/scripts/pipeline/getdsl_to_file.py <work_dir>/mastergo_raw.json --short-link <URL>`
   Do not read or paste `mastergo_raw.json`; inspect it only through bounded `scripts/query/dsl_query.py` commands.
3. Run preprocessing:
   `python tac-skills/tac-ui-mastergo/scripts/pipeline/pipeline.py <work_dir>/mastergo_raw.json <work_dir> <android_res_dir> --short-link <URL>`
4. Verify:
   - `mastergo_raw.json` exists and is valid JSON
   - `pipeline_result.json` records `file_context` with `fileId` and `rootLayerId`
   - `pipeline_result.json.status` is `SUCCESS` or `DEGRADED`
   - Repeating list/card structures have `structural_hints.json.list_metrics` with item size, pitch/gap, and divider ownership

## Phase A+: Blocking Clarification Gate

1. Do not generate `clarification_candidates.json` or `clarification_decisions.json`.
2. If the user provided a design screenshot, copy/persist it as `<work_dir>/design_screenshot.png` before render-scope confirmation and perform **macro layout frame analysis** on the screenshot first. Use the screenshot to identify the page's overall visible regions/modules, visual hierarchy, and approximate spatial arrangement, for example: left tab/sidebar, center content/list, top toolbar/filter area, lower banner, right detail panel, floating controls, bottom navigation, and likely page-owned vs shell/system areas. This screenshot-derived macro layout frame is an authoritative input to the render-scope question and to the later blueprint's high-level decomposition, but it does not replace DSL for exact geometry/tokens.
3. Build a combined candidate-region model by cross-checking the screenshot-derived macro layout frame with `skeleton_tree.json`, `structural_hints.json`, `pipeline_result.json`, bounded `scripts/query/dsl_query.py` output, and `scripts/query/query_semantic_mapping.py` output. The combined model must contain both sides of evidence: screenshot role/approximate location (e.g. "左侧 Tab 栏", "中部列表", "底部 banner") and mapped DSL node names/IDs/bounds when available. If no screenshot is provided, identify candidate renderable regions/modules from DSL-derived artifacts only. Do not read `mastergo_raw.json` or `semantic_mapping.json` directly.
4. Mandatory render-scope confirmation (blocking): after Phase A and before any Phase B work, pause and ask the user to confirm which region/modules should be rendered. This is a required question; do not continue until the user answers. The confirmation must be based on the combined screenshot+DSL candidate-region model when a screenshot exists.
5. The required question must summarize the detected macro layout frame, candidate modules, and concrete choices. If a screenshot was provided, lead with the screenshot-derived overall layout and then show mapped DSL node names/IDs when available. For example:
   - `我已结合设计截图和 DSL 识别出页面宏观布局：左侧可能是 Tab 栏，中间可能是列表区域，下方可能是 Banner；对应 DSL 候选模块为：<模块列表>。你需要实现哪些区域？`
   - `A. 全部截图可见业务区域`
   - `B. <推荐实现区域列表>`
   - `C. 指定区域：<列出可选区域/模块编号/名称>`
   - `D. 其他：请直接输入要渲染的区域、模块名称或补充说明`
6. Persist the user's render-scope answer to `user_decisions.json` with `source: "user"` before Phase B. When the answer is based on screenshot choices, record `evidence: ["design_screenshot.png", "mapped_dsl_nodes"]` and preserve the screenshot macro-region labels, approximate positions, and DSL mapping used in the question. Treat this confirmed render scope as an authoritative downstream reasoning basis: all later DSL analysis, macro layout frame design, page-structure analysis, module inclusion/exclusion, coordinate normalization, parent-relative/root-normalized bounds, layout ownership, and position inference must be derived from or constrained by this conclusion. After confirmation, query and analyze DSL only for the confirmed scope and any necessary ancestors/coordinate context; do not let unrelated DSL regions override the confirmed screenshot/user scope. Ensure the chosen scope is reflected in `recursive_blueprint.json`, `handoff_facts.json`, `handoff_prompt.md`, and the optional page UI spec if the user chooses to generate it. Mode B must also reflect it in `render_plan.md` when planning before coding.
7. After the mandatory render-scope answer is received, continue without further user interruption when a safe evidence/default strategy exists:
   - Text/icon/image uncertainty -> use placeholders and record unresolved items downstream.
   - Interaction uncertainty -> do not implement business behavior; record TODO/placeholder intent.
   - Component semantics uncertainty -> use DSL geometry plus `scripts/query/query_semantic_mapping.py` and `scripts/query/query_widget_registry.py` evidence.
8. Ask additional follow-up questions only if the unresolved fact would materially change coordinate normalization, static-vs-dynamic structure, reusable layout ownership, WT widget mapping, required interaction behavior, or data-binding shape.
9. When asking any follow-up question, present 2-3 concrete choices and do not continue until answered.
10. If any script/workflow-default decision must be persisted, write it to optional `user_decisions.json`. Only `source: "user"`, `source: "script"`, or `source: "workflow_default"` are allowed; never persist LLM self-decisions as final facts.

## Phase B: Blueprint

1. Read `references/03_blueprint_guide.md`.
2. Read `prompts/recursive_blueprint.md`.
3. Generate `recursive_blueprint.json`.
4. Verify:
   - Valid JSON
   - All skeleton nodes accounted for exactly once
   - No unresolved `needs_human_review`
   - Every optional `user_decisions.json` item is reflected
   - Excluded shell chrome is marked with `exclude_from_layout: true`
   - Excluded shell chrome records `coordinate_space`, `system_chrome_edge`, and `normalization_contribution`
   - Coordinate normalization offsets are recorded once with `applied_at: "root_renderable_children"`
   - Depth-0 renderable nodes use `coordinate_space: "root_normalized"` when top/left chrome is excluded
   - Every node has DSL-derived `bounds.raw` and `bounds.parent_relative`; root renderable children also have `bounds.normalized`
   - Bounds used in the blueprint were obtained from bounded `scripts/query/dsl_query.py node/children` output, not by reading `mastergo_raw.json` directly
   - Every non-null `list_metrics_ref` exactly matches `structural_hints.json.list_metrics[].container_id`; otherwise use `list_metrics_override`
   - Every skeleton node is accounted for by direct emission or exactly one ancestor `coverage.covered_subtree_ids`

## Phase B.5: Handoff Excerpt Index

1. Read `prompts/handoff_facts.md`.
2. Generate `handoff_facts.json` as a canonical **excerpt index**, not a duplicated fact database.
3. `handoff_facts.json` must be derived from `recursive_blueprint.json`, `pipeline_result.json`, `skeleton_tree.json`, `structural_hints.json`, `token_registry.json`, optional `user_decisions.json`, and bounded query outputs only. Do not read `mastergo_raw.json` or `semantic_mapping.json` directly.
4. The file must store references (`artifact` + `json_pointer` + `node_id`) and only short excerpts for quick review. Do not copy full blueprint subtrees, full token lists, full semantic mappings, or full structural hints.
5. The file must index:
   - Confirmed render scope from Phase A+ and its decision reference
   - Screenshot-derived region inventory references when `design_screenshot.png` was provided
   - Included/excluded module references and short reasons
   - Coordinate normalization reference and key bounds references
   - Layout reuse references
   - Dynamic/list metrics references or overrides
   - Widget/text/color/typography/image-icon references
   - Edge-case and unresolved-item references
   - Mode B contract references and TODO checklist references
6. Merge the user-facing Mode A summary into `handoff_facts.json.summary_view` in Chinese. `summary_view` must include page structure, ASCII diagram, decisions, controls/styles, implementation plan, and pending confirmations. Every factual summary section must list supporting references instead of becoming a separate source of truth.
7. If `user_decisions.json` contains the Phase A+ render-scope decision, reference it exactly in `handoff_facts.json.confirmed_render_scope.decision_ref`; do not paraphrase it into a different scope.
8. After this phase, later Markdown documents must not independently re-infer page scope, module inclusion/exclusion, coordinate normalization, or positions. They must point to or summarize `handoff_facts.json` references. If a conflict is found, fix `handoff_facts.json` or `recursive_blueprint.json` first, then regenerate dependent documents.
9. Verify `handoff_facts.json` is valid JSON and contains `kind: "handoff_excerpt_index"`, non-empty `confirmed_render_scope`, `module_index`, `summary_view`, and `mode_b_contract`.

## Phase B+: User-Facing Summary And Handoff Prompt

1. Read `handoff_facts.json` first and treat it as the source of truth.
2. Do not generate a separate `mode_a_summary.md`. The Mode A summary lives in `handoff_facts.json.summary_view` to avoid duplicate summary sources.
3. Read `templates/handoff_prompt.md`.
4. Generate `handoff_prompt.md` in Chinese as a short operational prompt for Mode B. It must point Mode B to `handoff_facts.json`, `recursive_blueprint.json`, `user_decisions.json` if present, and `prompts/render_plan.md` for pre-coding planning, and must explicitly say that confirmed scope and coordinate policy are not to be reinterpreted.
5. The user-facing summary in `handoff_facts.json.summary_view` must include:
   - Page structure paragraph
   - ASCII diagram
   - User/workflow decision detail if any
   - Recognized controls, text, colors, typography, image/icon summary
   - Implementation plan
   - User confirmation items
   - Supporting refs for every factual section
6. Consistency rule: `handoff_prompt.md` must point to the same confirmed render scope refs, coordinate policy refs, included module refs, excluded chrome refs, and unresolved refs as `handoff_facts.json`. Do not duplicate large fact tables; cite refs and short excerpts instead.
7. Do not generate `render_plan.md` in Mode A. Render planning is deferred to Mode B immediately before coding to preserve task continuity.

## Phase B++ Optional: Page UI Spec

1. Do not generate the page UI spec as part of the required handoff.
2. After the required Mode A handoff artifacts are generated and `validate_handoff.py <work_dir>` passes, ask the user whether to generate the optional page UI spec document.
3. Use this blocking question in Chinese and wait for the user answer:
   - `Mode A 交接已完成并通过校验。是否需要额外生成页面 UI 规格说明书？`
   - `A. 生成 page_ui_spec 文档`
   - `B. 不生成，直接结束`
4. Only if the user chooses to generate it:
   - Read `templates/page_ui_spec.md`.
   - Query the document governance constitution (`.specify/memory/document-governance-constitution.md`) to find the target folder for design specs, which is `<project_root>/persistent-assets/design/_baseline/ui/`.
   - Extract the page name `xxxx` from `handoff_facts.json.page_ref.name_ref.excerpt` when available, otherwise from `pipeline_result.json` when available, otherwise from a bounded root `scripts/query/dsl_query.py` query; do not read `mastergo_raw.json` directly.
   - Generate the page UI spec directly into `<project_root>/persistent-assets/design/_baseline/ui/page_ui_spec_xxxx页面.md` in Chinese.
   - The page UI spec must cite `handoff_facts.json` refs and short excerpts instead of duplicating large fact tables.
   - Re-run `validate_handoff.py <work_dir>` after writing the optional doc; validation should still pass.

## Required Handoff Artifacts

- `mastergo_raw.json`
- `skeleton_tree.json`
- `token_registry.json`
- `semantic_mapping.json`
- `user_decisions.json` if user/script/workflow-default decisions were persisted
- `colors_patch.xml`
- `dimens_patch.xml`
- `text_appearances_patch.xml`
- `structural_hints.json`
- `pipeline_result.json` (contains `file_context` metadata)
- `recursive_blueprint.json`
- `handoff_facts.json`
- `handoff_prompt.md`
- `<project_root>/persistent-assets/design/_baseline/ui/page_ui_spec_xxxx页面.md` only if the user opted to generate the optional page UI spec
- `design_screenshot.png` if provided by the user

## Final Validation

Run:

```bash
python tac-skills/tac-ui-mastergo/scripts/pipeline/validate_handoff.py <work_dir>
```

Expected result for the required handoff: `ALL PASS`. The optional page UI spec must not be required for `ALL PASS`.

If validation fails because a Markdown document is inconsistent with `handoff_facts.json`, do not patch the Markdown in isolation. First correct the canonical index or source artifact, then regenerate dependent Markdown from the canonical index.

## Stop Condition

After required validation passes, ask whether to generate the optional page UI spec. If the user declines, report the handoff summary from `handoff_facts.json.summary_view` and stop. If the user accepts, generate the optional page UI spec, re-run validation, report the handoff summary, and stop. Do not proceed to Mode B unless the user explicitly asks for rendering.
