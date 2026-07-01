# Operating Model Reference

Load this file only for general questions about boundaries, terminology,
storage, collaboration, or cross-project reuse.

## Terms

- `UX handoff`: behavior-oriented interaction handoff produced by this skill.
- `UI coordination`: mapping between interaction objects and UI carriers; not a
  pixel-perfect UI artifact.
- `downstream contract`: stable semantic names and ownership labels consumed by
  later coding or UI work.
- `interaction fact`: behavior truth supported by interaction, business,
  requirement, or explicit confirmation evidence.
- `visual evidence`: UI structure or carrier evidence that supports mapping but
  does not define behavior by itself.
- `implementation suggestion`: code-placement or reuse guidance that supports
  execution without becoming design truth.
- `ownership conflict`: unresolved ownership between page-local, shared,
  host-owned, or global scope.

## Boundaries

Mode A and Mode C output documentation by default: UX handoff, change log,
impact matrix, validation result, optional code conflict report, and lightweight
next-step guidance.

Mode B may output code changes only after an approved handoff is validated and
blocking ambiguity is resolved.

Without explicit implementation request, code-related output is limited to
file/module placement proposals, interface/state sketches, skeleton plans,
TODOs, and conflict/reuse reports.

## Coordination With UI Landing

Use `tac-ux-mastergo` for behavior truth: semantics, rules, state model, data
rules, navigation, boundary states, and acceptance checks.

Use visual/UI landing skills such as `tac-ui-mastergo` for pixel-perfect layout,
resources, platform UI artifacts, and visual restoration.

Coordinate through stable names:

- page or flow semantic name
- state names
- event/intent names
- effect names
- interaction target IDs
- component roles and visual node references

Do not put pixel values, typography, colors, or asset extraction rules in the UX
handoff unless they affect interaction behavior.

## Storage

When the handoff will guide implementation or collaboration, store it in a
controlled project documentation or specification path. Do not treat `.agents/`,
`.codex/`, or other tool-runtime folders as the long-term source of truth.

The skill does not mandate a fixed filename or directory. Use the target
project's documentation governance.

## Common Patterns

### Interaction Input Only

Run Mode A. Produce behavior truth, state model, pending visual gaps, and
provisional skeleton guidance. Do not finalize visual fidelity.

### Interaction + Visual Input

Run Mode A. Produce the handoff with UI coordination mapped to visual carriers.
Keep interaction truth and visual mapping separate.

### Visual Completion Later

Run Mode C. Refine UI coordination, carrier roles, and missing-state placement.
State whether only UI mapping changed or confirmed interaction facts also
changed.

### Skill Upgrade Without Input Change

Run Mode C. Classify the update as `structural-only`,
`analysis-enrichment`, or mixed. Newly surfaced constraints must be traced to
existing evidence and must not be presented as new requirements.

## Quality Bar

A valid handoff answers:

- What page or flow is being built?
- What evidence supports each confirmed rule?
- What states, events, effects, and transitions exist?
- What boundary states and recovery paths exist?
- What data is required and what data must not be used?
- What belongs to page-local, host-owned, shared, or global scope?
- What remains uncertain and who should confirm it?
- What code conflicts exist, if code was inspected after the handoff?

Prefer trigger-condition-result wording for key rules, so downstream coding
agents can implement behavior without inventing guards or effects.
