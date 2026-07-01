# Render Plan Generation Prompt

You are a senior Android architect producing a **Render Plan** document for the code generation phase.
This document serves as the "implementation brief" that bridges Phase 1 (global analysis) and Phase 2 (recursive code generation).

## Data Source Integrity

> **`handoff_facts.json` is the canonical excerpt index for this document.**
> Do not independently re-infer render scope, module inclusion/exclusion, coordinates, offsets, layout ownership, or decisions.
> **Detailed visual properties remain in `token_registry.json` and are referenced by `handoff_facts.json`.**
> You do NOT need to list every color or text style again. Provide high-level reuse and edge-case guidance with refs/pointers, not duplicated long tables.

## Inputs You Will Receive

1. **`handoff_facts.json`**: Canonical excerpt index for confirmed render scope, decisions, coordinate policy refs, module refs, reuse refs, edge-case refs, unresolved refs, summary_view, and Mode B contract
2. **`recursive_blueprint.json`**: Level-by-level structural decomposition from Phase B; use only to verify or expand facts already present in `handoff_facts.json`
3. **`token_registry.json`**: Extracted design tokens with semantic key mappings
4. **`skeleton_tree.json`**: Lightweight topology for cross-referencing node relationships
5. **Bounded `scripts/query/dsl_query.py` output**: On-demand, depth-limited DSL evidence only if a fact is missing; do not read the full raw file directly
6. **Bounded `scripts/query/query_semantic_mapping.py` output**: Widget, attr, text-style, and unresolved semantic hints for specific node IDs only if a fact is missing. Do not read `semantic_mapping.json` directly.
7. **`user_decisions.json`** (optional): Persisted user/script/workflow-default decisions that must be carried into Mode B without reinterpretation

## Output Format

Produce a Markdown document (`render_plan.md`) with the following EXACT structure.

---

### Section 0: User / Workflow Decisions

Summarize `handoff_facts.json.confirmed_render_scope.decision_ref` and all items from `handoff_facts.json.decision_refs`:

- Decision ID
- Source (`user`, `script`, or `workflow_default`)
- Topic, if present
- Affected node IDs
- Final decision
- Mode B impact

If there are no persisted decisions beyond the mandatory render scope, write: `No additional user/workflow decisions persisted.`

### Section 1: Layout Reuse Strategy

Based on `handoff_facts.json.layout_reuse_refs`:

- **Shared layouts**: Nodes that MUST use the same layout file via `<include>`. List:
  - Layout file name
  - Node IDs that share it
  - Differences between instances (if any, e.g., different text content or different width/height that must remain instance-level overrides)
- **Similar but distinct**: Nodes that LOOK similar but have structural differences that prevent reuse
  - Why they cannot be reused (different child count, different dimensions, etc.)

### Section 2: Special Rendering / Edge Cases

List complex rendering requirements from `handoff_facts.json.coordinate_policy_refs`, `handoff_facts.json.edge_case_refs`, and `handoff_facts.json.unresolved_refs`:

- Excluded demonstration chrome (status bar, shell title bar, bottom dock/tab bar, side rail)
  and the resulting coordinate normalization offsets
- Decorative accent bars or shell-edge strips that should stay excluded from implementation, and
  why they are decoration rather than a real sidebar/navigation module
- Nodes with overlapping children (`ol: true` in skeleton)
- Nodes where computed spacing is 0 or negative (possible absolute positioning)
- Nodes with complex gradient fills that may need custom drawable
- Background vs. Content images
- Nodes whose `scripts/query/query_semantic_mapping.py` output still contains `unresolved` items
- Any non-standard visual spec like "gradient overlay on image" or "text with opacity 0.6".

### Section 3: High-Level Task Checklist

Generate a brief TODO list for tracking the upcoming Mode B coding work. This plan is written immediately before coding starts, so every task must remain unchecked (`- [ ]`). Do not use `- [x]`, `- [/]`, "generated", "lint pass", or any wording that claims implementation work is complete. Format:

```markdown
- [ ] Read `layout_android_xml.md` (code generation rules)
- [ ] Read optional `user_decisions.json` if present and apply user/script/workflow-default decisions without reinterpretation
- [ ] Query `semantic_mapping.json` through `scripts/query/query_semantic_mapping.py` and prioritize resolved widget/attr/resource hints
- [ ] Identify excluded system chrome and record normalized top/bottom/side offsets before writing XML
- [ ] Recursively generate XML layouts for all nodes (Level 0 -> Level N)
- [ ] Data Binding: Generate Adapter + Data Model for all dynamic components
- [ ] Phase D: Run `pipeline/extract_assets.py` to fetch icon assets and replace placeholders
- [ ] Phase E (Optional): If design screenshot provided, run `pipeline/apply_text_mapping.py` to calibrate text
- [ ] Final: Lint check and build verification
```

## Constraints

1. Keep it brief and focused. Do not enumerate every terminal node.
2. Output valid Markdown. Use proper heading hierarchy (##, ###).
3. Do not introduce a new decision that contradicts `handoff_facts.json`, `user_decisions.json`, or authoritative decisions already reflected in `recursive_blueprint.json`.
4. Section 3 must contain TODOs only. A completed or in-progress checkbox is invalid before coding starts.
5. Every node ID, decision ID, coordinate offset, unresolved item, and source pointer mentioned here must exist in `handoff_facts.json` or the referenced source artifact.
6. If `handoff_facts.json` is incomplete, stop and update `handoff_facts.json` first instead of filling gaps directly in this Markdown document.
7. Prefer reference wording such as `see handoff_facts.json#/coordinate_policy_refs/normalization_ref` instead of duplicating long source content.
