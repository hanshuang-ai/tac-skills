---
name: tac-ui-mastergo-test
version: 0.4.5
description: >
  Batch-validates the existing tac-ui-mastergo skill against one or more MasterGo
  short links, produces per-case and campaign-level reports, and guides
  iterative fixes to tac-ui-mastergo when control recognition, semantic mapping,
  or pipeline behavior regress.
---

# Mastergogogo Test

Use this skill when the user wants to validate or regression-test
`tac-skills/tac-ui-mastergo` with one or more MasterGo layouts, compare
results across links, or iteratively improve `tac-ui-mastergo` based on repeated
failures.

## Scope

This skill evaluates Mode A semantics and preprocessing behavior. It does not
generate Android XML by default.

Focus on:

1. Raw DSL acquisition health
2. Pipeline health
3. Control-semantic recognition quality
4. Weak matches that rely on `node.name`
5. Duplicate child-layer matches inside already confirmed widgets
6. Widget-registry baseline regressions
7. Concrete iteration targets inside `tac-ui-mastergo`

## Read First

Before running any validation batch, read:

- [evaluation_contract.md](references/evaluation_contract.md)

## Preferred Runtime

Use the bundled Python runtime on this machine:

```powershell
C:\Users\TINNOVE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
```

Do not use the default `python` command unless you have already verified it.

## Workflow

### Mode 0: Run the local style-standardization regression case

Trigger:

- The user asks to verify the new text-style normalization logic
- The user asks to validate both semantic-mapping scripts and prompt rules
- The user asks to regression-test the latest `styleRef` / `ownership` / `conflicts` behavior

Run:

```powershell
& '<python>' '.agents\skills\tac-ui-mastergo-test\scripts\run_style_standardization_regression.py' `
  'build\tac-ui-mastergo_test\style_standardization_regression'
```

This deterministic regression case reuses the checked-in MasterGo DSL snapshot at
`build\mastergo_sjao1rny_mode_a\mastergo_raw.json` and validates:

1. `widget_registry.json` text-style metadata
2. `semantic_mapping.json` style normalization outputs
3. required prompt snippets in `layout_android_xml.md`

### Mode 0B: Run the local icon-placeholder regression case

Trigger:

- The user asks to verify shared-library icon replacement behavior
- The user asks to validate `extract_assets.py` placeholder replacement logic
- The user asks to regression-test canonical icon mapping such as `All/ic_all_account`

Run:

```powershell
& '<python>' '.agents\skills\tac-ui-mastergo-test\scripts\run_icon_placeholder_regression.py' `
  'build\tac-ui-mastergo_test\icon_placeholder_regression'
```

This deterministic regression case reuses the local DSL snapshot at
`build\root_dsl_check_SjuM1e5f\mastergo_raw.json` and validates:

1. canonical icon names map to shared widget-library drawables
2. `extract_assets.py replace` rewrites placeholder drawables correctly
3. skill/prompt/asset-guide rules stay aligned with the shared-library-first convention

### Mode 1: Validate a batch of links

Trigger:

- The user provides multiple MasterGo short links
- The user asks to validate `tac-ui-mastergo`
- The user asks for regression testing after a skill change

Run:

```powershell
& '<python>' '.agents\skills\tac-ui-mastergo-test\scripts\run_tac-ui-mastergo_validation.py' `
  'build\tac-ui-mastergo_test\<campaign>' `
  --short-link '<url-1>' `
  --short-link '<url-2>'
```

Or with a file:

```powershell
& '<python>' '.agents\skills\tac-ui-mastergo-test\scripts\run_tac-ui-mastergo_validation.py' `
  'build\tac-ui-mastergo_test\<campaign>' `
  --links-file 'build\tac-ui-mastergo_test\<campaign>\links.txt'
```

If short-link fetch fails with `WinError 10013` or a similar socket error,
rerun the command with escalated permissions. Do not misdiagnose that as a
Python dependency problem.

### Mode 2: Iterate `tac-ui-mastergo` after a failing batch

Trigger:

- The batch report shows repeated weak matches, duplicate descendants, or
  missing mappings
- The user asks to improve `tac-ui-mastergo` based on validation output

Process:

1. Read `campaign_summary.md` and the failing `case_report.md` files
2. If the failure is registry-related, inspect `build_widget_registry.py` and `widget_semantic_rules.json` before touching prompts
3. Patch the smallest responsible file under `tac-skills/tac-ui-mastergo`
4. Prefer deterministic fixes in scripts or mapping rules over prompt-only fixes
5. Rerun only the failed cases first
6. Compare the new campaign summary against the previous one

## Output Contract

Each validation campaign writes:

- `campaign_summary.json`
- `campaign_summary.md`
- `iteration_backlog.md`
- `cases/<case>/mastergo_raw.json`
- `cases/<case>/semantic_mapping.json`
- `cases/<case>/case_summary.json`
- `cases/<case>/case_report.md`
- `cases/<case>/fetch.log`
- `cases/<case>/pipeline.log`

## Evaluation Rules

Apply these priorities when interpreting a case:

1. `componentInfo.description`
2. `componentInfo.properties`
3. `styles.token`
4. `node.name`

Treat `node.name` as supporting evidence, not the authority.

Treat `runtime_only` widgets as valid semantic recognition when they are backed by strong evidence. They are not direct XML-render targets, so the test skill should not flag them as regressions solely for being runtime-only.

Confirmed regressions usually look like:

- explicit component nodes are not mapped
- only `node.name` is carrying widget resolution
- child layers inside a confirmed widget subtree are promoted into widgets
- widget-registry counts or required public controls regress
- pipeline succeeds but semantic output is weak

## Reporting Style

For each batch, report:

1. Which links passed cleanly
2. Which links exposed weak or duplicate matches
3. The top 1-3 iteration targets inside `tac-ui-mastergo`
4. Whether the next step is “fix scripts/rules” or “add more coverage cases”

Do not stop at “the batch ran successfully” if the semantic quality is poor.
