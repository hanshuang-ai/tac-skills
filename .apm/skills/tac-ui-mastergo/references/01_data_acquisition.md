# Step 1-2: Data Acquisition & Pipeline Preprocessing

> Read this file BEFORE executing Steps 1-2 of the workflow.

## Table of Contents

1. [Step 1: Fetch Raw DSL via MCP](#step-1-fetch-raw-dsl-via-mcp)
2. [Step 2: Pipeline Preprocessing](#step-2-pipeline-preprocessing)
3. [Pipeline Output Artifacts](#pipeline-output-artifacts)
4. [Pipeline Degradation Handling](#pipeline-degradation-handling)
5. [Checkpoint Gate](#checkpoint-gate-before-step-3)

---

## Step 1: Fetch Raw DSL To Disk

> [!IMPORTANT]
> **Only write raw DSL directly to disk.**
> Do **NOT** call or paste `mcp__getDsl(...)` in chat context, and do **NOT** read `mastergo_raw.json` directly.
> Use `scripts/pipeline/getdsl_to_file.py` to save `mastergo_raw.json`, then use bounded `scripts/query/dsl_query.py` commands for inspection.

### Preferred: Direct-to-disk fetch

Use the bundled helper:

```bash
python scripts/pipeline/getdsl_to_file.py <work_dir>/mastergo_raw.json --short-link <URL>
```

Or with explicit identifiers:

```bash
python scripts/pipeline/getdsl_to_file.py <work_dir>/mastergo_raw.json --file-id <fileId> --layer-id <layerId>
```

What it does:

- Resolves `shortLink` -> `fileId` + `layerId` when needed
- Calls the `/mcp/dsl` backend directly and writes the response to disk without chat output
- Writes the **full** payload to `<work_dir>/mastergo_raw.json`
- Writes `<work_dir>/pipeline_result.json` immediately containing `file_context`
- Can also be reused for rare component-master fallback fetches with `--skip-file-context`; normal Mode B node inspection uses `dsl_query.py`
- Preserves enough `componentId` context for later component-master lookups when INSTANCE nodes hide WT widget semantics locally

Token resolution order:

1. `--token`
2. `MG_MCP_TOKEN`
3. `MASTERGO_API_TOKEN`
4. `~/.claude.json` -> `mcpServers.mastergo-magic-mcp.env.MG_MCP_TOKEN`

### Bounded Inspection: DSL Query Helper

After `mastergo_raw.json` exists, inspect only small slices with `scripts/query/dsl_query.py`:

```bash
python scripts/query/dsl_query.py node <work_dir>/mastergo_raw.json --node-id <layerId> --depth 1 --max-children 20
python scripts/query/dsl_query.py children <work_dir>/mastergo_raw.json --node-id <parentId> --depth 1 --max-children 20
python scripts/query/dsl_query.py find <work_dir>/mastergo_raw.json --type TEXT --limit 20
python scripts/query/dsl_query.py ancestors <work_dir>/mastergo_raw.json --node-id <nodeId>
```

Keep `--depth`, `--max-children`, and `--limit` explicit. Use `--output <small_query.json>` when you want to save bounded evidence without printing it into chat. Use `--include-urls` or `--include-path-data` only for the specific node that needs asset/path processing.

> [!CAUTION]
> If `scripts/pipeline/getdsl_to_file.py` is unavailable or fails, stop and report the acquisition failure. Do not fall back to chat-context getDsl.

### Output Structure

```json
{
  "dsl": {
    "styles": { "paint_*": {...}, "font_*": {...}, "effect_*": {...} },
    "nodes": [...]
  },
  "componentDocumentLinks": [...],
  "rules": [...]
}
```

### Extracting fileId from Short Link

If only a `shortLink` is provided, resolve it to obtain the `fileId` (recorded for traceability and any explicit direct-to-disk fallback fetches):

```python
import urllib.request
response = urllib.request.urlopen(short_link)
# Parse fileId from the redirect URL: ...?file=<fileId>&layer_id=<layerId>
```

Record `fileId`; Mode B should normally query the cached root DSL with `scripts/query/dsl_query.py` instead of performing subtree getDsl calls.

> [!TIP]
> `scripts/pipeline/getdsl_to_file.py` already performs this resolution and writes `pipeline_result.json`
> for root acquisition, so you do not need to repeat it manually when using the preferred path.
> For rare direct-to-disk component fallback files, use `--skip-file-context` to avoid rewriting sibling context files.

---

## Step 2: Pipeline Preprocessing

Run the preprocessing pipeline:

```bash
python scripts/pipeline/pipeline.py <work_dir>/mastergo_raw.json <work_dir> <android_res_dir> --short-link <URL>
```

This executes 3 sub-steps sequentially:

| Sub-step | Script | Output |
|:---|:---|:---|
| 1. Extract skeleton | `pipeline/extract_skeleton.py` | `skeleton_tree.json` (lightweight topology, ~92% compression) |
| 2. Extract tokens | `pipeline/extract_tokens.py` | `colors.xml`, `text_appearances.xml`, `dimens.xml`, `token_registry.json` |
| 3. Analyze structure | `pipeline/analyze_structure.py` | `structural_hints.json` (repeating patterns, spacing) |

Semantic extraction expectation:
- `pipeline/extract_semantic_mapping.py` resolves widget semantics. If an INSTANCE lacks local metadata, inspect its `componentId` master. Backfill WT match onto the INSTANCE entry in `semantic_mapping.json`.

---

## Pipeline Output Artifacts

After successful pipeline execution, verify the following files exist in `<work_dir>/`:

- [ ] `skeleton_tree.json` -- Lightweight topology for global blueprint analysis
- [ ] `token_registry.json` -- Extracted tokens with semantic key mapping
- [ ] `structural_hints.json` -- Script-detected patterns (repeating siblings, spacing)

And in `<work_dir>/`:

- [ ] `colors_patch.xml` -- Additive color token patch suggestions
- [ ] `dimens_patch.xml` -- Additive dimension token patch suggestions
- [ ] `text_appearances_patch.xml` -- Additive typography token patch suggestions

> **IMPORTANT (Resource Merging)**: `extract_tokens.py` currently emits additive `*_patch.xml`
> files into `<work_dir>/`. Merge them selectively during Mode B instead of overwriting project
> resources wholesale.
> **Note on extract_tokens**: `pipeline/extract_tokens.py` currently emits additive `*_patch.xml`
> files into `<work_dir>/`. Merge them selectively during Mode B instead of overwriting project
> resources wholesale.

---

## Pipeline Degradation Handling

| Pipeline Result | What Happened | How to Proceed |
|:---|:---|:---|
| `SUCCESS` | All 4 sub-steps completed | Use all artifacts as planned, but access queryable artifacts only through their query scripts. |
| `DEGRADED` | Skeleton extraction failed | Stop and regenerate if possible; if user accepts degraded mode, inspect only bounded `scripts/query/dsl_query.py` slices. |
| `SUCCESS` with warnings | Some non-critical steps had issues | Use available artifacts. Missing data is inferred from bounded query-script output during code gen. |

---

## Checkpoint Gate: Before Step 3

Before proceeding, verify:

1. `mastergo_raw.json` exists and is valid JSON
2. `fileId` has been recorded under the `file_context` key in `pipeline_result.json`
3. Pipeline status is `SUCCESS` or `DEGRADED` (not a hard failure)
4. Any manual DSL inspection used bounded `scripts/query/dsl_query.py` output rather than direct raw JSON reads
5. Any semantic mapping inspection used `scripts/query/query_semantic_mapping.py` output rather than direct `semantic_mapping.json` reads
6. If `DEGRADED`, confirm which artifacts are missing and note for later steps

**PASS**: Return to `references/mode_a_workflow.md` and proceed to the Blocking Clarification Gate. Do not read Mode B asset-processing rules in Mode A.
**FAIL**: Report the failure to the user with root cause and pipeline logs.
