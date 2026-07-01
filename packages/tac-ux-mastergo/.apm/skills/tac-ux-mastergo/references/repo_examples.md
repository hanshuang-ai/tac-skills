# Usage Examples

Use these examples only as prompt patterns. Replace placeholder paths and
business nouns with the target project's own artifacts.

## Example 1: New Handoff From Interaction Input

Use when interaction specs, annotations, requirement notes, or flow diagrams are
available and no approved UX handoff exists yet.

```text
Use $tac-ux-mastergo in Mode A: UX Planner.

Interaction source:
<MasterGo interaction URL or fileId/layerId>

Optional supporting sources:
- Requirements: <path or link>
- Visual design: <MasterGo visual URL or fileId/layerId>
- Architecture notes: <path or link>

Target handoff:
<controlled-project-doc-path>/<page-or-flow>-ux-handoff.md

Goals:
- identify page/flow semantics and data ownership
- extract behavior rules with sources
- build state, event, effect, transition, and boundary-state models
- separate page-local, host-owned, shared, and global rules
- map interaction targets to visual carriers when visual input exists

Constraints:
- produce the UX handoff before reading implementation code
- treat visuals as mapping evidence, not behavior truth
- stop after documentation unless implementation is explicitly requested
```

Expected output:

1. UX handoff saved or drafted.
2. Validation result.
3. Blocking or non-blocking pending items.
4. Optional next step for UI landing or implementation.

## Example 2: Existing Handoff Maintenance

Use when the handoff already exists and the task is to update it because source
input changed, a visual design arrived, or the skill/template/checker evolved.

```text
Use $tac-ux-mastergo in Mode C: Handoff Maintenance.

Existing handoff:
<controlled-project-doc-path>/<page-or-flow>-ux-handoff.md

Maintenance reason:
<interaction-design-update | skill-structural-upgrade | skill-analysis-enrichment | mixed>

New or unchanged sources:
- <MasterGo interaction URL or fileId/layerId>
- <MasterGo visual URL or fileId/layerId>
- <requirement or confirmation source>

Constraints:
- preserve confirmed downstream contract names unless evidence requires change
- distinguish structural cleanup, analysis enrichment, and real input changes
- do not use current code as behavior evidence
```

Expected output:

1. Updated handoff.
2. Change log and impact matrix.
3. Statement of whether business rules changed.
4. Validation result.

## Example 3: Implementation From Approved Handoff

Use only when the user explicitly asks to implement after a handoff exists.

```text
Use $tac-ux-mastergo in Mode B: Implementation Follow-Up.

Approved UX handoff:
<controlled-project-doc-path>/<page-or-flow>-ux-handoff.md

Implementation scope:
- <controller/view-model/state files>
- <view/layout/component files>
- <shared capability files when the handoff requires them>

Constraints:
- validate the handoff before editing code
- implement only the smallest behavior delta required by the handoff
- keep existing code as implementation material, not business truth
- update the handoff pending/conflict sections if implementation exposes gaps
```

Expected output:

1. Handoff validation result.
2. Files changed.
3. Implemented handoff rules.
4. Remaining conflicts or pending items.
5. Verification commands and results.

## Pending Item Handling

- Stop immediately when the gap can change the target page/flow, truth source,
  state model, data ownership, navigation, effects, rule ownership, or
  acceptance.
- Continue with an explicit assumption when the gap only affects local wording,
  temporary naming, visual polish, or other details that will not send coding in
  the wrong direction.
- Merge same-root questions so each role receives a short, actionable
  confirmation list.
