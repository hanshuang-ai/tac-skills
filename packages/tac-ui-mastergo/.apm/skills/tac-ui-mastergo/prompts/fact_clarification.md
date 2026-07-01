# Deprecated Fact Clarification Prompt

This prompt is deprecated.

Do not generate `clarification_candidates.json` or `clarification_decisions.json`.

Use the Phase A+ **Blocking Clarification Gate** in `references/mode_a_workflow.md` instead:

1. If `design_screenshot.png` is provided, analyze the screenshot first to identify overall visible regions/modules, then map those regions to DSL nodes with bounded query outputs. Otherwise inspect `skeleton_tree.json`, `structural_hints.json`, `pipeline_result.json`, bounded `scripts/query/dsl_query.py` output, and bounded `scripts/query/query_semantic_mapping.py` output only when needed. Do not read `mastergo_raw.json` or `semantic_mapping.json` directly.
2. Always ask the mandatory render-scope confirmation. If a screenshot was provided, present screenshot-derived regions first and persist the user's answer before downstream DSL analysis. Ask additional questions only when the unresolved fact would materially change page scope, coordinate normalization, static-vs-dynamic structure, reusable layout ownership, WT widget mapping, required interaction behavior, or data-binding shape and no safe evidence/default exists.
3. Use placeholders/TODOs for non-blocking text, icon, image, or interaction uncertainty.
4. Persist only confirmed `source: "user"`, `source: "script"`, or `source: "workflow_default"` decisions in optional `user_decisions.json`.
5. Never persist LLM self-decisions as final facts.
