---
name: tac-ux-mastergo
version: 0.4.8
description: >
  Analyze MasterGo interaction designs and optional requirement/design
  documents to produce AI-readable UX implementation handoff documents for
  coding agents. Use when the user provides MasterGo interaction specs, page
  sketches, annotations, flowcharts, requirement docs, MasterGo visual designs,
  or architecture docs and asks for interaction analysis, business logic
  extraction, state modeling, SDD/spec generation, interaction/design mapping,
  implementation handoff docs, conflict checking, iteration of an existing
  handoff, or skeleton guidance. Default output is documentation, not code.
  Current code may be inspected only after the design-derived handoff exists,
  as a conflict/reuse reference, never as the business-rule source of truth.
---

# MasterGo UX Interaction Handoff

Turn MasterGo interaction material into a behavior-oriented UX handoff that a
coding agent can implement without inventing business rules. Default output is
documentation; write production code only when the user explicitly asks for
implementation after a handoff exists.

## Activation

When this skill is loaded, immediately read the `version` field from this file's
frontmatter and output it before starting any analysis or workflow step:

```
[skill:tac-ux-mastergo:v{version from frontmatter}]
```

## Hard Rules

- **DSL 截断检测强制**: 每次 `mcp__getDsl` 调用必须使用 `maxOutputLength ≥ 500000`；获取后必须立即通过 `cache_dsl.py validate-truncation` 验证完整性。若检测到截断（`RESULT: truncated`），翻倍 `maxOutputLength` 重试，直到 `RESULT: complete`。禁止在未通过截断检测的 DSL 上继续分析。
  as the only behavior truth sources.
- When a MasterGo interaction source is a long explanation board, mixed canvas,
  or one layer containing multiple sections/states/pages, scan the whole board
  first and enumerate all visible sub-scenarios before extracting local rules.
  Do not lock onto only the most visually prominent region.
- **全量文本标注扫描（Flowchart & Annotation Sweep）**: 当 DSL 同一层中包含
  设计说明区、页面 mockup 区、流程图标注区等多个视觉分组时，必须在提取规则前
  对**所有 TEXT 节点**做全量扫描并分类：
  1. 按 DSL 节点坐标 (x, y) 将 TEXT 节点归入其所在视觉区域
  2. 每个区域的 TEXT 节点均视为一等交互证据，不允许仅提取"设计说明"标题下的
     文本而跳过流程图侧标、连线旁标注、页面框旁注释等区域
  3. 扫描完成后，将提取的文本集合与最终业务规则清单交叉校验：每个有交互语义的
     TEXT 节点必须对应一条规则，或被显式标记为"不入规则"并给出理由
  (Validator: `validate_feedback_copy` 现已检测 §6.3 文本覆盖率；全量 TEXT 覆盖率
  检测已纳入 Mode A §2 自检步骤)
- Treat visible feedback copy as first-class interaction truth. Toasts, black
  prompt bubbles, error tips, empty-state text, success/failure messages, and
  labels beside flowchart branches must be extracted verbatim and bound to their
  trigger condition, source state, target state, and effect. Do not collapse
  multiple visible feedback messages into a generic "show error" rule.
- Treat visual design as UI mapping evidence, not behavior truth, unless the
  behavior is explicitly annotated or confirmed.
- Treat existing code only as conflict, reuse, or implementation-planning input
  after the handoff exists.
- Keep UX behavior separate from pixel-perfect UI restoration; use
  `tac-ui-mastergo` only for visual landing work.
- Keep shared/global protocols separate from page-local behavior. If ownership
  is ambiguous and can change implementation direction, mark an ownership
  conflict instead of force-fitting it.
- Preserve traceability for confirmed rules and mark direction-changing gaps as
  `pre-blocking` or `blocking`.
- When the MasterGo design has not changed since the last fetch, reuse locally
  cached trimmed DSL files instead of re-requesting `mcp__getDsl`. Use
  `scripts/cache_dsl.py check` to verify cache validity and
  `scripts/cache_dsl.py save` to persist fresh data.
- Interaction analysis consumes only trimmed DSL: node names, annotations,
  interaction properties, visible text, and mapping anchors. Visual properties
  (color, font, coordinates, shadow, borders, image URLs) are stripped at
  cache-write time. Both raw and trimmed DSL are preserved under
  `.cache/tac-ux-mastergo/`.
- When multiple MasterGo interaction links are provided (each pointing to a
  different page, popup, or global rule), run
  `scripts/intake_layer_inventory.py parse` to emit a navigation table to
  stdout and write it into `ux_handoff_index.md` before analysis. Present the
  index to the user for scope confirmation. Do not blindly fetch DSL for every
  link.
- When `待确认项` contains `pre-blocking` or `blocking` items, auto-search the
  project for a requirements document (PRD) before asking the user: check
  `PROJECT.md`, `AGENTS.md`, `specs/`, `doc/`, and `docs/` for files
  containing `PRD`, `需求`, `requirement`, `spec`, `设计`, or `验收`. If found,
  use it to resolve pending items; if not found or insufficient, prompt the
  user to provide one. Do not let PRD silently override interaction evidence.
- Do not create any file not declared in the Output Contract. Pending-item
  summaries are cross-referenced only through `ux_handoff_index.md`; standalone
  summary, combined report, or final-report files are forbidden.
- Before writing any output, resolve the output directory from the Output
  Contract section below. If the section cannot be read, do not guess — ask
  the user for the target directory.
- When `待确认项` contains `blocking` or `pre-blocking` items after handoff
  generation, do NOT auto-route by AI-judged `确认角色`. Instead:
  1. Present all blocking/pre-blocking items to the developer with
     AI-suggested confirmation roles.
  2. Developer triages each item: items they can confirm immediately are
     resolved in-session; items needing PM/UX confirmation are deferred to an
     external confirmation sheet.
  3. Developer may re-route items (change role) before sheet generation.
  4. Generate `ux_confirmation_sheet.xlsx` via
     `scripts/gen_confirmation_sheet.py` only for deferred items.
  5. Developer reviews the xlsx before sending to external stakeholders.
  Use `templates/ux_confirmation_sheet_spec.md` for the xlsx structure spec.
- Record all MasterGo source links only in `ux_handoff_index.md`. Per-entity
  handoffs reference the index ("链接见 index") instead of duplicating links.
- Do not write more than one user action (click, toggle, swipe, long-press,
  confirm, cancel, show, hide, navigate, popup, back, input) per business-rule
  row. Each rule MUST represent a single trigger-condition-result triplet and
  use at most one `→` in its description. Split compound rules immediately
  when extraction reveals multiple independent actions — compound rules are not
  allowed as confirmed rules. (Validator: `validate_rule_granularity`)
- Do not omit sub-state modeling when an interaction object has two or more
  visible states annotated in DSL. For every such object, either create a
  sub-state group in §5 状态模型 or explicitly mark "no independent state" to
  signal intentional omission. The handoff validator checks the coverage ratio
  of §3 interaction-object count versus §5 sub-state-group count.
  (Validator: `validate_sub_component_coverage`)
- Do not merge two or more distinct visible feedback texts into a single
  handoff rule or feedback-copy row. Every visible toast, prompt bubble,
  button-state label, error tip, success message, empty-state copy, and
  inline status text must occupy its own independent row in §6.3
  Feedback Copy Inventory, bound to its own trigger event and guard condition.
  (Validator: `validate_feedback_copy`)

## MasterGo 链接规范

输入 MasterGo 链接时必须遵守以下约束：

1. **禁止使用短链接**：短链接（如 `uxd.tinnove.com.cn/s/xxx`）存在失效和权限限制风险，请使用完整链接。
2. **必须提供 `file_id` 和 `layer_id`**：两者缺一不可。缺失任一参数将导致无法定位目标图层。`page_id` 非必需，工具链不依赖此参数。

示例：

```
https://uxd.tinnove.com.cn/file/141186755153304?fileOpenFrom=home&devMode=true&layer_id=1565%3A16701
```

## Prerequisites

| 依赖 | 适用范围 | 安装方式 |
|:--|:--|:--|
| **Python 3.3+** | 全部模式 | 系统自带或 [python.org](https://python.org) |
| `openpyxl` | 仅生成/回放 `ux_confirmation_sheet.xlsx` 时 | `pip install openpyxl` |
| MCP: `mcp__getDsl` | Mode A；Mode C 当维护原因为 `interaction-design-update` 且涉及 MasterGo 设计变更时 | IDE 环境需接入 MasterGo MCP Server；**大画板（5000+ px）需 `maxOutputLength ≥ 500000`** |
| MCP: `mcp__getMeta` | 同上（用于缓存版本判重） | 同上 |

> - 6 个核心脚本（`validate_ux_handoff`、`validate_ux_gate`、`cache_dsl`、`intake_layer_inventory`、`validate_iteration`、`validate-truncation`）仅依赖 Python 标准库，兼容 Python 2.7+。
> - 2 个 xlsx 脚本（`gen_confirmation_sheet`、`replay_confirmation`）依赖 `openpyxl`，要求 Python 3.6+。
> - `openpyxl` 仅在需要生成/回放 `.xlsx` 确认单时才需要（Mode A/C 待确认项外部确认流程）。
> - `validate_iteration.py` 通过 `subprocess` 调用同目录下其他脚本（L1~L4 自检），不引入额外外部依赖。
> - Mode B 不需要 MCP 工具，仅在已有 Handoff 文档上操作。

## Mode Routing

Choose one mode before loading detailed references:

| Mode | Use when | Load |
|:--|:--|:--|
| 0. Input Intake | Multiple MasterGo links provided; need to inventory, deduplicate, and cache DSL before analysis. **Pre-condition of Mode A**, not a standalone mode. | `scripts/intake_layer_inventory.py`, `scripts/cache_dsl.py` |
| A. UX Planner | New interaction/business truth is provided and a handoff, rule model, state model, or mapping is needed. | `references/mode_a_workflow.md`, `templates/ux_handoff.md`, validators |
| B. Implementation Follow-Up | The user explicitly asks to implement from an existing UX handoff. | `references/mode_b_workflow.md`, existing handoff, relevant code, validators |
| C. Handoff Maintenance | An existing handoff must be updated because inputs changed, visuals arrived, the skill/template/checker changed, or analysis should be enriched without changing interaction input. | `references/mode_c_maintenance_workflow.md`, `references/capability_registry.md` (degradation detection rules), existing handoff, needed source artifacts, validators |

> When multiple MasterGo links are provided, run Mode A step 0 first:
> `scripts/intake_layer_inventory.py`, `scripts/cache_dsl.py`.

For general questions about boundaries, storage, collaboration, or reuse, load
`references/operating_model.md`. For prompt examples, load only the relevant
section of `references/repo_examples.md`.

## Output Contract

All handoffs are written to `persistent-assets/design/_baseline/04-UX总体设计` by
default. If the user explicitly specifies an output directory, use the user-specified
directory instead. If the target directory does not exist, create it before writing.

Modes A and C produce:

```
{output-dir}/
├── ux_handoff_index.md            # always — navigation, coverage, global index
├── ux_handoff_{page-or-flow}.md   # one per page/flow entity
├── ux_handoff_global_{topic}.md   # optional — complex independently-implementable global rules
├── ux_confirmation_sheet.xlsx     # conditional — when external-role blocking items are deferred
└── ...
```

`ux_confirmation_sheet.xlsx` is **not a truth source** and is **not tracked in
git**. It is a collaboration transit artifact. Confirmed conclusions are
ultimately written back into handoff §15 待确认项 (markdown). Lifecycle:
generated → reviewed (by dev) → in-flight (sent to PM/UX) → replayed (conclusions
applied to handoff) → deleted/archived. See
`templates/ux_confirmation_sheet_spec.md`.

**ux_handoff_index.md** uses `templates/ux_handoff_index.md` and contains three sections:
- 交互稿清单与进度 — combined source-link registry + navigation + coverage-status table (one row per input entity)
- 全局/跨页规则 — simple rules expanded inline; complex rules point to `ux_handoff_global_{topic}.md`
- 待确认项汇总 — aggregated pending items from all per-entity handoffs

**Global/cross-page rule placement — SPLIT, do not bundle:**
- **Simple** rules (toast specs, badge display, input field behavior, page frame
  layout — constraints expressible in a few lines without state machines) MUST
  be expanded inline inside `ux_handoff_index.md`'s `全局/跨页索引` section.
- **Complex** independently-implementable rules (state machines, download
  queues, permission recovery, cross-page sync) MUST each get a dedicated
  `ux_handoff_global_{topic}.md`.
- `ux_handoff_global_shared_rules.md` as a single catch-all file is
  **FORBIDDEN**. If only one complex global rule exists, create
  `ux_handoff_global_{topic}.md` with the specific topic name, never a generic
  "shared_rules" file.

Each page/flow handoff uses `templates/ux_handoff.md` and must expose input
evidence, semantics, interaction objects, rules, states, events, effects,
transitions, boundary states, navigation, data expectations, global/shared
ownership, UI coordination, implementation suggestions, optional code conflicts,
pending confirmations, and acceptance checks.

When the source contains flowcharts or state diagrams, the handoff must include
a transition/effect inventory that preserves every branch label and visible
feedback copy verbatim. For each toast or prompt, record at minimum: copy text,
trigger event, condition, whether it blocks the side effect, whether user input
is preserved, and implementation owner. If a visible copy is not currently
implementable because the backend or SDK does not support the condition, keep
the copy in the handoff and mark the capability gap separately instead of
deleting the rule.

### `{name}` 命名推导

占位符 `{page-or-flow}` / `{name}` 按以下流程推导：

| 步骤 | 来源 | 说明 |
|:--|:--|:--|
| 1 | DSL 节点名 | 从 MasterGo 层节点名称或用户确认中获取 |
| 2 | 类型判断 | 页面 / 弹窗 / 流程 / 全局规则 → 用对应语义关键词 |
| 3 | 去重与消歧 | 同名实体用编号或子场景名消歧（如 `download_result` / `download_history`） |
| 4 | 统一风格 | 全小写 + 下划线分隔（snake_case），英文优先 |

`{topic}` 命名同样遵循以上 4 步规范。示例：`download_button`（非 `download_button_shared`）、`payment_flow`、`account_session`。

### 产物允许/禁止内容

| 产物文件 | 允许内容 | 禁止内容 |
|:--|:--|:--|
| 页面 Handoff (`ux_handoff_{name}.md`) | 交互事实、业务规则、状态模型、反馈文案、边界态、过渡效果清单 | 视觉细节（尺寸、颜色、字体、坐标、圆角、阴影） |
| 全局规则 Handoff (`ux_handoff_global_{topic}.md`) | 共享协议、跨页同步、恢复规则 — 仅限复杂规则，一个 topic 一个文件 | 页面私有的入口 UI、空态文案、本地布局；禁止将所有全局规则合并为一个 `shared_rules` 文件 |
| Index (`ux_handoff_index.md`) | 导航表、覆盖率、**简单全局规则内联展开**、源链接 | 内部缓存路径（`.cache/`）、临时文件引用；禁止将复杂规则全文塞入 index |

Mode B may produce code changes only after handoff validation passes and
blocking ambiguity is resolved.

## Validation

Use validators whenever producing a gate decision or saved handoff:

```bash
python <skill-dir>/scripts/validate_ux_gate.py input --mode A --has-new-truth-source true --has-existing-handoff false --target-identifiable true
python <skill-dir>/scripts/validate_ux_gate.py input --mode B --has-new-truth-source false --has-existing-handoff true --target-identifiable true
python <skill-dir>/scripts/validate_ux_gate.py input --mode C --has-new-truth-source false --has-existing-handoff true --target-identifiable true
python <skill-dir>/scripts/validate_ux_handoff.py <handoff.md>
python <skill-dir>/scripts/intake_layer_inventory.py validate --index <output-dir>/ux_handoff_index.md
python <skill-dir>/scripts/gen_confirmation_sheet.py --handoff-dir <output-dir>
python <skill-dir>/scripts/replay_confirmation.py --xlsx-dir <output-dir> --handoff-dir <output-dir>
```

For Mode A and Mode C, run the input gate before creating or editing a handoff.
If the gate fails, stop instead of producing a best-effort handoff.

Treat validation failures as blockers. Treat warnings as review items unless the
target is a template or intentionally incomplete placeholder.

Validation pass does not imply execution readiness. `PASS` only means the
handoff structure is valid enough for review. After validation, always run a
confirmation gate against `待确认项`:

- if any `pre-blocking` item exists, stop immediately and request confirmation
- if any `blocking` item exists, stop before implementation or further landing
  work and request confirmation
- only `non-blocking` items may be carried forward without pausing, and they
  must be surfaced explicitly in the final output

Always report two conclusions separately:

- `Validation result`: `PASS` / `FAIL`
- `Execution readiness`: `ready` / `pause-for-confirmation`

Developer tool: `scripts/validate_iteration.py` validates skill correctness across
L1 (syntax), L2 (functional correctness), L3 (trimming fidelity), and L4
(documentation consistency) layers. Run it after modifying scripts, templates,
or workflow references.

## Stop Conditions

- Stop after documentation in Mode A or C unless implementation is explicitly
  requested.
- Stop and request a truth source when no interaction/business artifact or
  existing handoff is available for the chosen mode.
- Stop before implementation when unresolved items can change state, data,
  navigation, side effects, ownership, UI carrier responsibility, or acceptance.
- Stop after handoff generation and run the developer triage routing when any
  `pre-blocking` or `blocking` pending item remains, even if the validator
  reports `PASS`. Items the developer can confirm immediately are resolved
  in-session; items requiring external confirmation are deferred to
  `ux_confirmation_sheet.xlsx` without blocking the current session.
- When a filled confirmation sheet is provided, replay it against the handoffs
  via `scripts/replay_confirmation.py` and resolve the reported categories
  (adopted → write into handoff; revised/conflict → developer reviews;
  unresolved → wait) before proceeding to code conflict checks or
  implementation.
- When interaction input did not change and only the skill evolved, label the
  update as `structural-only`, `analysis-enrichment`, or mixed; separate newly
  surfaced constraints from actual requirement changes.
