# <Project / Feature> Self-Test Case Planning Document

**Status**: Draft  
**Created**: <date>  
**Owner**: <team / role>  
**Scope**: <product, feature, release, platform>  

## 1. Objective

Describe what this plan enables and what success means. State that concrete test cases are generated in a later step.

## 2. Source Discovery Summary

| Source Type | Path / Location | Evidence Level | Use |
|-------------|-----------------|----------------|-----|
| Entry point | `<path>` | A/B/C/D | Project rules and document priority |
| Requirement | `<path>` | A | Product behavior and acceptance |
| Design / UX | `<path>` | A/B | Page states and user journeys |
| Spec / Quickstart | `<path>` | A/B | Feature paths and acceptance checks |
| API / Contract | `<path>` | A/B | Non-UI verification |
| Existing tests | `<path>` | B/C | Style, selectors, baseline coverage |

## 3. Authority Order

List the source precedence for conflicts. Example:

1. Approved requirements and acceptance standards.
2. Approved interaction/design mapping.
3. Feature spec and quickstart.
4. API and interface contracts.
5. Existing tests and implementation.

## 4. Coverage Strategy

| Priority | Meaning | Coverage Rule |
|----------|---------|---------------|
| P0 | Critical path | Must be covered or blocked with a reason |
| P1 | Important regression | Cover by automation or manual checklist |
| P2 | Secondary/edge | Sample or defer with reason |

## 5. Execution Type Criteria

| Type | Criteria |
|------|----------|
| Maestro | Visible UI path with stable operations and assertions |
| Maestro + Setup | UI path requiring prepared data, permissions, accounts, mocks, or environment |
| Manual | Human judgment, external service, physical device, system flow, weak network, or visual fidelity |
| Unit/Contract | Data, state, API, schema, sorting, business rule, bridge, SDK, or platform contract |
| Out of Scope | Future/deprecated/blocked/no current testable expectation |

## 6. Module-by-Module Plan

### <Module Name>

| Verification Point | Source | Priority | Execution Type | Handoff Target | Notes |
|--------------------|--------|----------|----------------|----------------|-------|
| <behavior to verify> | `<path>#<section>` | P0 | Maestro | `<candidate id>` | <setup/risk> |

## 7. Maestro-First Backlog

| Candidate ID | Module | Goal | Source | Required Setup | Notes |
|--------------|--------|------|--------|----------------|-------|
| `<case_id>` | <module> | <goal> | `<path>` | <none/setup> | <selector/data risk> |

## 8. Manual Verification Backlog

| Item ID | Module | Goal | Source | Manual Reason | Notes |
|---------|--------|------|--------|---------------|-------|
| `<manual_id>` | <module> | <goal> | `<path>` | <reason> | <device/service needed> |

## 9. Unit/Contract Backlog

| Item ID | Module | Goal | Source | Target Layer | Notes |
|---------|--------|------|--------|--------------|-------|
| `<contract_id>` | <module> | <goal> | `<path>` | <unit/api/contract> | <existing test or gap> |

## 10. Coverage Summary

| Module | P0 Count | P1 Count | Maestro | Maestro + Setup | Manual | Unit/Contract | Blocked |
|--------|----------|----------|---------|------------------|--------|---------------|---------|
| <module> | <n> | <n> | <n> | <n> | <n> | <n> | <n> |

## 11. Risks and Open Questions

| Risk / Question | Impact | Owner | Decision Needed |
|-----------------|--------|-------|-----------------|
| <risk> | <impact> | <owner> | <decision> |

## 12. Downstream Handoff

| Field | Value |
|-------|-------|
| Intended next Skill | <skill name or role> |
| Scope included | <modules and priorities> |
| Source bundle | <paths> |
| Maestro candidates | <count/list> |
| Manual-only items | <count and reasons> |
| Unit/Contract items | <count and target areas> |
| Required setup | <device/data/account/network/mock requirements> |
| Open questions | <blocking questions or none> |

| Candidate ID | Module | Goal | Source | Execution Type | Downstream Notes |
|--------------|--------|------|--------|----------------|------------------|
| `<candidate_id>` | <module> | <goal> | `<path>` | Maestro | <notes for case writer> |

