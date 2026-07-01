# Mode B Implementation Follow-Up Workflow

Use this file only after entry routing selects Mode B.

## Context Loading Contract

Mode B may read:

- the approved UX handoff document
- `scripts/validate_ux_handoff.py`
- current code paths needed to implement the handoff
- project architecture or coding standards required by the target codebase

Mode B must not read:

- `references/mode_a_workflow.md` as a replacement for the approved handoff
- unrelated design-analysis notes
- broad implementation areas outside the handoff scope
- `tac-ui-mastergo` rendering prompts unless the user explicitly asks for visual
  landing too

## Goal

Implement the smallest interaction delta required by the approved handoff. Do not
reinterpret business rules from current code.

## Preflight

1. Confirm `ux_handoff_index.md` exists and contains approved handoff entries.
2. Identify the target handoff file(s) from the index navigation table.
3. For each target handoff, run:

   ```bash
   python <skill-dir>/scripts/validate_ux_handoff.py <handoff.md>
   ```

4. If validation fails, stop and fix or ask for handoff clarification before code
   edits.
5. If implementing a page that depends on global rules, also load the
   corresponding `ux_handoff_global_{topic}.md` or read the global index section
   in `ux_handoff_index.md`.
6. Identify the implementation scope from the handoff:
   - states
   - events/intents
   - effects
   - data rules
   - navigation
   - boundary states
   - global/shared capabilities
7. Read only the code paths needed for that scope.

## Phase A: Conflict And Reuse Check

Before editing code, classify current implementation against the handoff:

- implemented
- missing
- wrong
- conflicting
- reusable
- needs confirmation

Inventory reusable capabilities separately:

- shared state model
- shared interaction protocol
- shared renderer, presenter, controller, binding layer, or equivalent
  interaction carrier
- page-local responsibilities

Do not create a page-private state machine or protocol when the handoff only
requires filtering, composition, navigation, or page-level governance around an
existing shared capability.

## Phase B: Implementation Plan

Create a short edit plan:

- files to change
- state/event/effect additions
- data rule changes
- navigation or host collaboration changes
- boundary-state behavior
- tests or verification commands

If a required business rule is missing or contradictory in the handoff, pause and
ask for clarification. Do not infer it from existing code.

## Phase C: Code Changes

Implement only the behavior required by the handoff:

- state
- intent/event
- effect/navigation/toast/dialog
- data selection, filtering, grouping, and refresh behavior
- click/focus/back behavior
- async transitions
- loading, empty, error, offline, disabled, and retry behavior

Avoid:

- unrelated refactors
- visual rewrites not required for interaction targets
- replacing shared capabilities without handoff evidence
- changing rules to fit current code

If implementation exposes a design ambiguity, update the handoff's `待确认项`
or conflict section rather than silently choosing a new product rule.

## Phase D: Documentation Sync

After code changes:

- update the handoff if implementation clarified a file/module placement,
  reusable capability, or unresolved item
- keep confirmed business rules unchanged unless the user confirms a design input
  correction
- record any remaining implementation gaps
- update the corresponding row in `ux_handoff_index.md` navigation table status

## Phase E: Verification

Run the smallest relevant verification:

- build or compile target
- unit tests if available
- feature-specific checks if the repo has them
- handoff validation if the handoff was updated

If verification fails because of environment/cache state, try one appropriate
cleanup or retry before attributing the failure to the code.

## Final Output

Report:

- index path (`ux_handoff_index.md`)
- target handoff path(s) and validation results
- files changed
- implemented handoff rules
- conflicts or pending items left open
- verification commands and results

Do not claim that visual fidelity is complete unless `tac-ui-mastergo` or an
equivalent visual workflow was also executed.
