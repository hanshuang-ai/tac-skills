# Handoff Excerpt Index Generation Prompt

You are generating `handoff_facts.json` as a **handoff excerpt index**, not a duplicated fact database.

## Purpose

`handoff_facts.json` is the canonical handoff index for Mode A downstream documents and Mode B. It freezes conclusions by referencing authoritative source artifacts with JSON pointers, node IDs, and short excerpts. It must avoid copying full structures from `recursive_blueprint.json`, `token_registry.json`, `structural_hints.json`, or `semantic_mapping.json`.

The Mode A user-facing summary is merged into this file as `summary_view`, so later Markdown documents can be thin views of this index rather than separate sources of truth.

## Allowed Inputs

- `recursive_blueprint.json`
- `pipeline_result.json`
- `skeleton_tree.json`
- `structural_hints.json`
- `token_registry.json`
- Optional `user_decisions.json`
- Optional `design_screenshot.png` and the screenshot-derived region inventory captured in `user_decisions.json` when provided
- Bounded `scripts/query/dsl_query.py` output when a missing bound/name must be verified
- Bounded `scripts/query/query_semantic_mapping.py` output for key node semantics

Do not read `mastergo_raw.json` or `semantic_mapping.json` directly.

## Output Requirements

Produce valid JSON only. Do not include Markdown fences or comments.

Use this top-level shape:

```json
{
  "version": 2,
  "kind": "handoff_excerpt_index",
  "source_of_truth": true,
  "source_artifacts": {
    "blueprint": "recursive_blueprint.json",
    "pipeline_result": "pipeline_result.json",
    "skeleton_tree": "skeleton_tree.json",
    "structural_hints": "structural_hints.json",
    "token_registry": "token_registry.json",
    "user_decisions": "user_decisions.json if present",
    "design_screenshot": "design_screenshot.png if present"
  },
  "macro_layout_frame_refs": [
    {"artifact": "recursive_blueprint.json", "json_pointer": "/macro_layout_frame/regions/0", "region_label_excerpt": "", "approx_position_excerpt": "", "mapped_node_ids": []}
  ],
  "page_ref": {
    "name_ref": {"artifact": "recursive_blueprint.json", "json_pointer": "", "excerpt": ""},
    "root_node_ref": {"artifact": "recursive_blueprint.json", "json_pointer": "", "node_id": "", "excerpt": ""},
    "canvas_ref": {"artifact": "recursive_blueprint.json", "json_pointer": "", "excerpt": "width x height only"},
    "file_context_ref": {"artifact": "pipeline_result.json", "json_pointer": "/file_context", "excerpt": "fileId/rootLayerId only"}
  },
  "confirmed_render_scope": {
    "decision_ref": {"artifact": "user_decisions.json", "json_pointer": "", "decision_id": "", "excerpt": "user answer only"},
    "selected_module_refs": [
      {"artifact": "recursive_blueprint.json", "json_pointer": "", "node_id": "", "name_excerpt": "", "bounds_ref": ""}
    ],
    "excluded_module_refs": [
      {"artifact": "recursive_blueprint.json", "json_pointer": "", "node_id": "", "name_excerpt": "", "reason_excerpt": ""}
    ],
    "screenshot_region_refs": [
      {"artifact": "user_decisions.json", "json_pointer": "", "region_label_excerpt": "", "mapped_node_ids": []}
    ],
    "downstream_rule": "All downstream DSL analysis, structure, coordinate normalization, layout ownership, and position inference must be constrained by this confirmed scope."
  },
  "decision_refs": [
    {"artifact": "user_decisions.json", "json_pointer": "", "decision_id": "", "topic_excerpt": "", "impact_excerpt": ""}
  ],
  "coordinate_policy_refs": {
    "normalization_ref": {"artifact": "recursive_blueprint.json", "json_pointer": "/coordinate_normalization", "excerpt": "offset values only"},
    "excluded_chrome_refs": [
      {"artifact": "recursive_blueprint.json", "json_pointer": "", "node_id": "", "edge_excerpt": "", "contribution_excerpt": ""}
    ],
    "key_bounds_refs": [
      {"artifact": "recursive_blueprint.json", "json_pointer": "", "node_id": "", "role_excerpt": "", "bounds_excerpt": "raw/normalized x,y,w,h only"}
    ]
  },
  "module_index": [
    {
      "node_id": "",
      "name_excerpt": "",
      "role_excerpt": "",
      "included_in_render_scope": true,
      "blueprint_ref": {"artifact": "recursive_blueprint.json", "json_pointer": ""},
      "bounds_ref": {"artifact": "recursive_blueprint.json", "json_pointer": ""},
      "dynamic_ref": null,
      "list_metrics_ref": null,
      "semantic_refs": [],
      "reason_excerpt": ""
    }
  ],
  "layout_reuse_refs": {
    "shared_layout_refs": [],
    "similar_but_distinct_refs": []
  },
  "semantic_index": {
    "widget_refs": [],
    "text_refs": [],
    "color_token_refs": [],
    "typography_token_refs": [],
    "image_icon_refs": []
  },
  "edge_case_refs": [],
  "unresolved_refs": [],
  "summary_view": {
    "language": "zh-CN",
    "page_structure": {"text": "", "supporting_refs": []},
    "ascii_diagram": {"text": "", "supporting_refs": []},
    "decisions": {"text": "", "supporting_refs": []},
    "controls_and_styles": {"text": "", "supporting_refs": []},
    "implementation_plan": {"text": "", "supporting_refs": []},
    "pending_user_confirmations": {"text": "无阻塞待确认项。", "supporting_refs": []}
  },
  "mode_b_contract": {
    "must_read_refs": [
      {"artifact": "handoff_facts.json", "reason": "canonical excerpt index and summary_view"},
      {"artifact": "recursive_blueprint.json", "reason": "full structure and bounds"},
      {"artifact": "user_decisions.json", "reason": "authoritative user decisions, if present"},
      {"artifact": "token_registry.json", "reason": "full token details"},
      {"artifact": "structural_hints.json", "reason": "full list/repetition metrics"},
      {"artifact": "prompts/render_plan.md", "reason": "Mode B planning template to generate render_plan.md immediately before coding"}
    ],
    "must_not_reinterpret": [
      "confirmed_render_scope",
      "decision_refs",
      "coordinate_policy_refs",
      "module inclusion/exclusion"
    ],
    "todo_checklist_refs": []
  }
}
```

## Reference Rules

1. Store facts as references whenever possible:
   - Use `artifact` + `json_pointer` for machine-readable source location.
   - Use `node_id` for DSL/blueprint nodes.
   - Use `excerpt` only for short labels, user answers, or compact `x,y,w,h` values needed for quick review.
2. Do not copy full child arrays, full token lists, full semantic mappings, or full blueprint nodes.
3. `summary_view` may contain Chinese prose and ASCII text, but every factual claim in it must list supporting refs in `supporting_refs`. If screenshot evidence exists, the page structure and ASCII diagram must cite `macro_layout_frame_refs` so the macro layout (such as left tab bar, center list, lower banner) is traceable.
4. `confirmed_render_scope` is mandatory after Phase A+. If no user scope decision exists, stop and ask for it instead of generating this file.
5. If `design_screenshot.png` was provided, include screenshot-derived region refs from `user_decisions.json` and ensure selected/excluded module refs are consistent with the user's screenshot-region confirmation.
6. Treat optional `user_decisions.json` as authoritative. Never replace it with LLM guesses.
7. If evidence is missing, add a small item to `unresolved_refs` with the missing source/ref. Do not invent common defaults like 8dp, 16dp, #333333, or generic font sizes.
8. `module_index` must make inclusion/exclusion explicit for every top-level or scope-relevant module, but each entry must be a reference entry, not a copied subtree.
