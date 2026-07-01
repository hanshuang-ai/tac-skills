---
name: "tac-testcase-plan"
version: 0.4.5
description: >
  Generate a reusable self-test case planning document before actual test case development.
  Use when the user asks to write a test plan, self-test plan, testing coverage plan, or
  prepare inputs for another test-case generation skill. The workflow focuses on reliably
  discovering project-specific inputs instead of assuming fixed paths, then producing a
  module-based plan that marks what can be automated by Maestro, what needs setup, what
  should stay manual, and what should be handed to unit/contract tests.
---

# Test Case Planning Skill

This Skill produces a planning document, not the final test cases. Its output must be good enough for a downstream Skill, such as a Maestro case writer, to generate concrete `.case.md`, YAML flows, manual cases, or unit/contract test tasks.

## Principles

1. Do not assume fixed repository paths. Discover reliable inputs from the current project.
2. Prefer authoritative project entrypoints, document indexes, specs, requirements, design mappings, quickstarts, API contracts, existing tests, and existing E2E assets.
3. Keep evidence traceable. Every planned verification point must cite at least one discovered input source.
4. Separate execution types clearly: `Maestro`, `Maestro + Setup`, `Manual`, `Unit/Contract`, or `Out of Scope`.
5. Mark uncertainty explicitly. Do not invent product requirements, page flows, selectors, or backend states.
6. Produce a plan that can be handed off without conversation context.

## Step 1: Define Scope

Extract the requested scope from the user:

| Field | Required | Guidance |
|-------|----------|----------|
| Product / app / subsystem | Yes | Infer from repo when obvious; ask only if multiple products are present. |
| Test goal | Yes | Foundation smoke, feature self-test, release regression, E2E coverage, etc. |
| Target platforms | No | Android, iOS, web, backend, embedded, mixed. Infer from build files when possible. |
| Automation target | No | Maestro, Playwright, unit tests, API tests, manual checklist. |
| Output path | No | If absent, place under the project documentation area discovered in Step 2. |

If scope is ambiguous and cannot be inferred from the repository, ask one concise question.

## Step 2: Discover Reliable Inputs

Use fast repository searches first. Prefer `rg --files` and `rg -n`.

### 2.1 Find governance and index files

Search for project-level entrypoints and document catalogs:

```text
AGENTS.md, PROJECT.md, README.md, CONTRIBUTING.md
docs index, document index, 文档索引, 文档治理, project context
.specify/memory, specs, requirements, design, docs, doc
```

Read entrypoints first when they exist. Use them to determine document priority, must-read rules, and module boundaries.

### 2.2 Find requirement and acceptance sources

Search file names and content for:

```text
PRD, requirement, requirements, 产品需求, 需求规格, SRS
acceptance, 验收, AC, success criteria, 用户故事, User Story
spec.md, quickstart.md, plan.md, tasks.md, contracts
```

Rank acceptance sources above implementation notes. If several sources conflict, keep the conflict in the plan and prefer the repository's documented authority order.

### 2.3 Find interaction, design, and UX sources

Search for:

```text
interaction, UX, UI, design, 交互, 设计, 原型, MasterGo, Figma
页面摘要, 交互与设计映射, 状态机, flow, navigation
```

Use these sources for page states, entry paths, visible behavior, dialog rules, boundary states, and manual visual checks.

### 2.4 Find API, contract, and state-machine sources

Search for:

```text
api, contract, schema, 接口, 协议, 状态, state, model, data-model
```

Use these sources to decide what belongs in `Unit/Contract` instead of UI automation.

### 2.5 Find existing test assets

Search for:

```text
e2e, maestro, playwright, cypress, detox, test, androidTest, cases, flows
coverage-matrix, .case.md, .yaml, .spec.ts
```

Existing tests are not requirements by themselves, but they reveal style, selectors, reset strategy, environment assumptions, and baseline coverage.

### 2.6 Record evidence quality

Classify every input you use:

| Level | Source type | Use |
|-------|-------------|-----|
| A | Requirement, acceptance standard, approved spec, contract, authoritative design mapping | May define expected behavior |
| B | Quickstart, implementation plan, page context, API guide, existing test case | May refine paths and setup |
| C | Source code, layouts, strings, selectors, screenshots | May confirm implementation and automation feasibility |
| D | Inference from naming or directory structure | Use only as a clue; do not define expected behavior |

## Step 3: Build the Module Map

Derive modules from discovered sources instead of imposing a fixed taxonomy.

Use these heuristics:

1. Product navigation: tabs, pages, routes, screens, activities, menus.
2. Business domains: account, order, search, payment, download, install, profile.
3. Cross-cutting rules: authorization, network boundary, permissions, offline, logging, analytics.
4. Platform components: SDKs, APIs, storage, background jobs, installers.
5. Existing test grouping: current E2E case folders or test packages.

For each module, list:

```text
module name
evidence sources
primary user journeys
states and edge cases
automation feasibility
coverage priority
handoff notes
```

## Step 4: Decide Execution Type

Use this decision table:

| Type | Choose when |
|------|-------------|
| `Maestro` | The behavior is visible in the app UI and can be reached by stable taps, text/id assertions, navigation, or simple waits. |
| `Maestro + Setup` | UI automation is possible but needs data preparation, clean app state, mock server, preinstalled app, permissions, account, feature flag, or network setup. |
| `Manual` | The check needs human judgment, real external service state, physical device operation, system permission flows, payment, weak-network realism, legal/content review, or visual fidelity. |
| `Unit/Contract` | The behavior is data mapping, sorting, state transition, API schema, version comparison, permission decision, bridge contract, or business rule not best verified through UI. |
| `Out of Scope` | The source mentions a future, deprecated, missing, or blocked area and gives no testable current expectation. |

Never label a path `Manual` only because automation is inconvenient. State the concrete blocker.

## Step 5: Generate the Plan

Use `references/plan-template.md` as the output structure. Adapt section names to the project, but keep these required sections:

1. Objective and scope.
2. Source discovery summary.
3. Evidence and authority order.
4. Coverage strategy and priority rules.
5. Execution type criteria.
6. Module-by-module plan.
7. Maestro-first backlog.
8. Manual verification backlog.
9. Unit/contract backlog.
10. Downstream handoff package.
11. Risks, blockers, and open questions.

The module-by-module plan must include a table with:

```text
verification point | source | priority | execution type | handoff target | notes
```

## Step 6: Handoff Contract

End the plan with a machine-readable handoff section that another Skill can consume:

```markdown
## Downstream Handoff

| Field | Value |
|-------|-------|
| Intended next Skill | <for example: tac-maestro-case / API test writer / manual case writer> |
| Scope included | <modules and priorities> |
| Source bundle | <list of paths> |
| Maestro candidates | <case ids or module paths> |
| Manual-only items | <count and reasons> |
| Unit/Contract items | <count and target areas> |
| Required setup | <device/data/account/network/mock requirements> |
| Open questions | <blocking questions or none> |
```

Also include a candidate backlog table:

```markdown
| Candidate ID | Module | Goal | Source | Execution Type | Downstream Notes |
|--------------|--------|------|--------|----------------|------------------|
```

## Step 7: Validate Before Finalizing

Check:

1. No source path is invented.
2. No module is listed without evidence.
3. Every P0/P1 module has at least one planned verification point or a documented blocker.
4. Each `Manual` item has a real manual-only reason.
5. Each `Maestro + Setup` item lists the setup dependency.
6. The downstream handoff section is self-contained.

If writing the plan to disk, report the file path and summarize the coverage by execution type.

