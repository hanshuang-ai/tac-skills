# Step 4: Recursive Blueprint Generation

> Read this file BEFORE executing Step 4 of the workflow.

## Table of Contents

1. [Purpose](#purpose)
2. [Input Preparation](#input-preparation)
3. [LLM Invocation](#llm-invocation)
4. [Blueprint Output Validation](#blueprint-output-validation)
5. [Graceful Degradation](#graceful-degradation)
6. [Ambiguity Protocol](#ambiguity-protocol)
7. [Checkpoint Gate](#checkpoint-gate-before-step-5)

---

## Purpose

This is the **key architectural step** that enables recursive code generation. The goal is to produce a `recursive_blueprint.json` that defines a **level-by-level** component decomposition, not a flat list.

The blueprint determines:
- Which nodes are **terminal** (generate complete layout in one pass)
- Which nodes are **non-terminal** (generate parent ViewGroup + recurse into children)
- Where repeating groups exist (-> RecyclerView patterns)
- Where homogeneous components exist (shared `componentId` -> reuse same layout)
- Which reusable INSTANCE families need component-master semantic carry-over before Mode B so WT widgets are not downgraded to generic Android views

---

## Input Preparation

Provide the LLM with these inputs:

| Input | Source | Required |
|:---|:---|:---|
| `skeleton_tree.json` | Pipeline Step 2 output | Yes |
| bounded `query/dsl_query.py` output | On-demand queries against `mastergo_raw.json` | Yes for geometry/bounds evidence |
| `structural_hints.json` | Pipeline Step 2 output | Optional (supplements analysis) |
| bounded `query/query_semantic_mapping.py` output | On-demand queries against `semantic_mapping.json` by node IDs | Optional but recommended for widget/content evidence |
| `user_decisions.json` | Optional Phase A+ persisted user/script/workflow-default decisions, including screenshot macro-region labels/mappings when provided | Optional |
| `design_screenshot.png` | User-provided screenshot for macro layout frame evidence; use only if present and already persisted by Phase A+ | Optional |
| `pipeline_result.json` | Integrated output: contains `file_context` metadata | Yes |

### Skeleton Field Reference

The skeleton uses abbreviated field names. If you need to interpret them, consult `references/05_dsl_schema.md` Section "Skeleton Field Abbreviations".

---

## LLM Invocation

1. Read the prompt from `prompts/recursive_blueprint.md`
2. Feed the prompt + inputs to the LLM
3. The LLM outputs `recursive_blueprint.json` with the schema defined in the prompt

The prompt file (`prompts/recursive_blueprint.md`) contains:
- Complete decision rules (homogeneous detection, repeating groups, positional patterns, scroll candidates, container selection, terminal conditions, card patterns, reusable fragments)
- Strict output JSON schema
- Constraints for valid output

When `structural_hints.json.list_metrics` exists, carry the matching list metric entry into the blueprint via `list_metrics_ref`. `list_metrics_ref` must be the exact `container_id` from `structural_hints.json.list_metrics`. If the structure analyzer missed an obvious list/grid, leave `list_metrics_ref` null and add a DSL-derived `list_metrics_override` with coordinates, item size, pitch, and gap evidence. This is required even for two-item preview lists because list spacing is a container contract, not part of the reusable item layout.

Before accepting the blueprint, verify that every emitted node includes `bounds.raw`, `bounds.parent_relative`, and (for renderable root children after chrome exclusion) `bounds.normalized`. Obtain these values through bounded commands such as `python scripts/query/dsl_query.py node <work_dir>/mastergo_raw.json --node-id <id> --depth 0`; do not read `mastergo_raw.json` directly. For semantic hints, query node IDs with `python scripts/query/query_semantic_mapping.py --mapping <work_dir>/semantic_mapping.json <nodeId> ...`; do not read `semantic_mapping.json` directly. Use the confirmed screenshot+DSL macro layout frame to guide high-level roles and decomposition order, then use machine-readable DSL bounds to determine exact side, alignment, and dimensions; do not rely on prose in `notes` for geometry.

Before invoking the blueprint prompt, verify the Phase A+ gate:

1. Do not require or generate `clarification_candidates.json` / `clarification_decisions.json`.
2. If `user_decisions.json` exists, it must be valid JSON and every item must use `source: "user"`, `source: "script"`, or `source: "workflow_default"` only.
3. If a decision was not confirmed by user/script/workflow default, do not hard-code it as a final fact. Let the blueprint derive structure from DSL evidence, or set `needs_human_review: true` when no safe default exists.
4. The blueprint prompt input should include `user_decisions.json` only when it exists.
5. If `design_screenshot.png` was provided, the blueprint prompt input must include the screenshot-derived macro layout frame from `user_decisions.json` so the top-level decomposition reflects both visual-region evidence and DSL structure.

**Do NOT duplicate the decision rules here.** The prompt file is the single source of truth.

---

## Blueprint Output Validation

After receiving the blueprint, validate:

1. **Structural completeness**: Every skeleton node is accounted for exactly once, either as a blueprint node or under one ancestor's `coverage.covered_subtree_ids`
2. **Parent-child consistency**: Non-terminal nodes' expanded children appear at the next level with matching `parent_id`
3. **fileId present**: `file_id` field is set (needed for traceability and any explicit direct-to-disk fallback fetches)
4. **No orphaned references**: Node IDs referenced in `repeating_groups`/`homogeneous` either appear as blueprint nodes or are covered by a delegated/terminal/list ancestor
5. **Terminal correctness**: Nodes marked `terminal: true` should NOT have descendants appearing at deeper levels
6. **Geometry correctness**: `bounds.raw` matches bounded `dsl_query.py` absolute DSL coordinates; `bounds.normalized` subtracts chrome offsets exactly once
7. **List metrics correctness**: Every non-null `list_metrics_ref` exactly matches an existing `structural_hints.json.list_metrics[].container_id`

---

## Graceful Degradation

If the skeleton is missing (pipeline returned `DEGRADED`):

1. Stop and regenerate preprocessing if possible; skeleton is the preferred topology input.
2. If the user explicitly accepts degraded planning, inspect only bounded DSL slices through `scripts/query/dsl_query.py`.
3. The blueprint is still required -- produce it from shallow query results only.
4. Focus on the top 2-3 levels of the hierarchy (avoid going too deep in a single pass).
5. Mark deeper sub-trees as `terminal: true` with `notes: "from bounded DSL query, may need further decomposition"`.

---

## Ambiguity Protocol

Mode A has two ambiguity layers:

- **Blocking clarification gate**: Phase A+ asks the user only when a fact would materially change scope, coordinate normalization, static-vs-dynamic structure, reusable layout ownership, WT widget mapping, required interaction behavior, or data-binding shape and no safe evidence/default strategy exists. Persist only user/script/workflow-default decisions in optional `user_decisions.json`; never persist LLM self-decisions as final facts.
- **Post-blueprint review**: `needs_human_review: true` is for ambiguities discovered while generating or validating the blueprint.

If any component in the blueprint output has `needs_human_review: true`:

1. **PAUSE** immediately -- do not proceed to code generation
2. Present the ambiguous component(s) to the user with:
   - What the component looks like (name, dimensions, children count)
   - Why it was flagged (e.g., unclear if it's a list or static group)
   - 2-3 multiple-choice options for resolution
3. Update the blueprint based on user response
4. Resume workflow

---

## Checkpoint Gate: Before Step 5

Before proceeding, verify:

1. `recursive_blueprint.json` exists and is valid JSON
2. All skeleton nodes are accounted for by node emission or `coverage.covered_subtree_ids` (no missing or duplicate coverage)
3. No `needs_human_review: true` items remain unresolved
4. `file_id` is set in the blueprint
5. Level structure is coherent (depth 0 is root, children at depth N+1)
6. Every node has DSL-derived machine-readable bounds; root-normalized bounds subtract excluded chrome exactly once
7. Every non-null `list_metrics_ref` resolves to an existing `structural_hints.json.list_metrics[].container_id`
8. If `user_decisions.json` exists, no item uses `source: "llm"`
9. Every persisted user/script/workflow-default decision is reflected in the affected blueprint node(s)

**PASS**: Return to `references/mode_a_workflow.md` and proceed to Render Plan generation.
**FAIL**: Fix blueprint issues or ask user for clarification.
