# Evaluation Contract

## Goal

Validate whether `tac-ui-mastergo` can reliably consume MasterGo DSL semantics
without over-trusting weak clues.

## Inputs

Accepted input forms:

1. Repeated `--short-link`
2. `--links-file`

`links.txt` supports:

- one URL per line
- `label|url`
- `label url`

Blank lines and lines starting with `#` are ignored.

## Per-Case Checks

Each case must evaluate:

1. fetch status
2. pipeline status
3. explicit component descriptions in raw DSL
4. resolved widgets in `semantic_mapping.json`
5. widget-registry baseline in `widget_registry.json`
5. strong matches:
   - `resolvedWidget` exists
   - evidence contains `componentInfo.description`
6. weak matches:
   - `resolvedWidget` exists
   - evidence does not contain `componentInfo.description`
7. descendant duplicate suspects:
   - a widget node is nested under another resolved widget of the same class
   - the child match does not have `componentInfo.description`
8. runtime-only matches:
   - `resolvedWidget` exists
   - `resolvedWidget.renderKind == runtime_only` or the widget is known runtime-only in the registry
   - this is acceptable when evidence is strong; do not treat runtime-only by itself as a regression
9. text-style normalization quality when the case contains `WTTextStyle*` signals:
   - `semantic_mapping.json.text.styleRef` resolves to a public `@style/...` reference
   - `semantic_mapping.json.text.styleFamily` / `styleVariant` are normalized
   - `semantic_mapping.json.text.ownership` exists for styled text nodes
   - `semantic_mapping.json.text.conflicts` captures mismatches between structured fields and `TEXT.name`
10. prompt contract stability for style-standardization cases:
   - `layout_android_xml.md` still contains the rules for `styleRef`, `ownership`, and `conflicts`
   - prompt regressions should be treated as test failures, not documentation-only drift
   - context-conflicted text colors are explicitly guarded: partial subtrees, generic `Primary Text`-style DSL copy, contradictory existing contrast, and no screenshot/full-page confirmation must preserve the current explicit text/icon color and mark `[UNRESOLVED: text color context conflict]`
11. icon placeholder replacement quality when the case contains canonical shared-library icons:
   - placeholders such as `@drawable/ph_icon_all_ic_all_account` are replaced with canonical shared drawables such as `@drawable/ic_all_account`
   - shared-library icons are not misreported as missing component masters
   - local extraction remains fallback-only for icons that do not map to canonical shared drawables

## Widget Registry Baseline

Treat the current registry floor as part of the contract:

- widgets: at least `74`
- text styles: at least `87`
- color resources: at least `358`
- runtime-only widgets: at least `7`

Required public widgets must remain present:

- `WTSideBar`
- `WTRadioButton`
- `WTFloatSeekBar`
- `WTNavigationGroup`
- `WTItemWindow`
- `WTChoiceChips`
- `WTNavigationBar`
- `WTProgressBar`
- `WTTitleBar`
- `WTTopSlideBar`
- `WTSwitch`

Required runtime-only widgets must remain present:

- `WTEmptyDialog`
- `WTPushDialog`
- `WTDatePickerDialog`
- `WTTimePickerDialog`
- `WTItemWindow`
- `WTSnackBar`
- `WTAutoBubble`

## Campaign Result Labels

- `PASS`
  - fetch ok
  - pipeline ok
  - no weak matches
  - no descendant duplicate suspects
  - registry baseline ok
  - all explicit component-description nodes are covered by strong matches

- `NEEDS_ITERATION`
  - pipeline runs, but semantic quality is not clean
  - examples: weak matches, duplicate descendants, missing strong mappings

- `BLOCKED`
  - fetch or pipeline failed hard

## Iteration Heuristics

Map repeated failures to the smallest likely fix:

- weak matches dominated by `node.name`
  - lower `node.name` authority
  - downgrade those hits to candidate-only output

- duplicate descendants inside confirmed widgets
  - add subtree de-duplication
  - reject child matches when an ancestor already owns the same widget class

- explicit `componentInfo.description` nodes not mapped
  - expand widget registry aliases or variant rules
  - inspect `extract_semantic_mapping.py` before changing prompts

- widget registry baseline drops
  - inspect `build_widget_registry.py`
  - inspect `widget_semantic_rules.json`
  - restore manual widgets, variant rules, and pure-color filtering before changing prompts

- fetch failures with socket errors
  - rerun with escalated network permissions

## Reporting

The agent should end each batch with:

1. a short pass/fail table
2. repeated issue categories
3. the top iteration target inside `tac-skills/tac-ui-mastergo`
