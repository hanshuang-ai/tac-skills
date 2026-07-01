# <case_id>

## Basic Info

| Field | Value |
|------|------|
| Case ID | <case_id> |
| Title | <title> |
| Feature | <feature> |
| Priority | P1 |
| Type | Maestro E2E |
| Owner | Test Tooling |

## Source Materials

| Source | Path | Section |
|------|------|------|
| Quickstart | specs/<feature>/quickstart.md | <section> |
| Spec | specs/<feature>/spec.md | <FR/AC> |
| Design | persistent-assets/design/_baseline/ui/<page>.md | <rule> |

## Traceability

| Requirement | Expected Behavior | Covered Step |
|------|------|------|
| <FR/AC/path> | <expected behavior> | <step number> |

## Preconditions

- <device/network/app state requirement>
- <package install/uninstall requirement>
- <debug-only activity or launcher requirement>

## Test Data

| Name | Value | Source |
|------|------|------|
| <name> | <value> | <source> |

## Device Requirements

- Device id: <deviceId or runtime input>
- Android version: <version if required>
- Network: <network requirement>
- Permissions: <permission requirement>

## Steps

1. <step>
2. <step>
3. <step>

## Expected Results

1. <expected result>
2. <expected result>
3. <expected result>

## Maestro Flow

- Flow path: `persistent-assets/automated-testing/_baseline/flows/<case_id>.yaml`
- Required script args: `<args>`

## Reset Strategy

- Before run: <reset command or script arg>
- After run: <cleanup command or note>

## Known Risks

| Risk | Mitigation |
|------|------|
| <risk> | <mitigation> |

## Execution Record

| Time | Device | Git Commit | Result | Artifacts | Bug |
|------|------|------|------|------|------|
| <time> | <device> | <commit> | <pass/fail> | <path> | <bug path or none> |
