# Mode A UX Planner Workflow

Use only after `SKILL.md` routes the task to Mode A.

## Goal

Create a UX handoff from new interaction/business truth input. Stop after the
handoff and optional conflict report. Do not edit production code in Mode A.

## Loading Contract

May read:

- `templates/ux_handoff.md`
- `templates/ux_handoff_index.md` when writing or updating the index
- `templates/ux_confirmation_sheet_spec.md` when generating or replaying a
  confirmation sheet
- interaction, requirement, business, visual, or architecture inputs
- `scripts/validate_ux_gate.py`
- `scripts/validate_ux_handoff.py`
- `scripts/intake_layer_inventory.py` when multiple links are provided
- `scripts/cache_dsl.py` for DSL cache lookup and persistence
- `scripts/gen_confirmation_sheet.py` for generating external confirmation xlsx
- `scripts/replay_confirmation.py` for replaying filled xlsx
- `references/repo_examples.md` only when prompt examples help

Must not read production code internals until the handoff is complete and the
user asks for conflict or readiness checking.

## Workflow

### 0. (Optional) Input Pre-Processing — Multi-Link Intake

When the user provides input, first decide whether a multi-link intake step is
needed:

**Single link** (user provides exactly one MasterGo interaction layer link):

1. Extract `file_id` and `layer_id` from the URL. MasterGo URLs follow the pattern:
   ```
   https://mastergo.com/file/{file_id}?layer-id={layer_id}
   ```
   If the URL uses a short link (e.g. `https://mastergo.com/s/abc123`), resolve
   it first via `mcp__getMeta` or browser redirect to get the canonical URL.

2. Call `mcp__getMeta` with the extracted `fileId` and `layerId` to get the
   current design version. Use the returned version string as `<version>` below.

3. Check the local cache with the extracted values:
   ```bash
   python <skill-dir>/scripts/cache_dsl.py check --file-id <extracted-file-id> --layer-id <extracted-layer-id> --version <version-from-getMeta>
   ```
   - `hit` → read the trimmed file at `TRIM_PATH` directly, use it as input for
     step 1. Skip MCP `mcp__getDsl`.
   - `miss` or `stale` → proceed to step 4.

4. Fetch DSL via `mcp__getDsl` with the extracted `fileId` and `layerId`.
   **Always use `maxOutputLength=500000` for the first attempt** — large
   design boards (5000+ px canvases) routinely exceed the default limit.

5. **IMPORTANT — Truncation check before caching.** After receiving the DSL
   response, write the raw JSON to a temporary file under `.cache/` and
   validate it is not truncated:

   **Step 5a — Write raw DSL to disk:**
   Use `write_to_file` to save the MCP response JSON to:
   ```
   {workspace}/.cache/tac-ux-mastergo/dsl_raw_{layer_id}.json
   ```
   (Replace `{layer_id}` with the actual layer ID, using `_` instead of `:`)

   **Step 5b — Validate:**
   ```bash
   python <skill-dir>/scripts/cache_dsl.py validate-truncation --input-file {workspace}/.cache/tac-ux-mastergo/dsl_raw_{layer_id}.json
   ```

   - `RESULT: complete` → proceed to step 6 with this JSON.
   - `RESULT: truncated` or `suspicious` → the DSL was cut off by MCP output
     limits. **Double the `maxOutputLength` (e.g., 500000 → 1000000) and
     re-fetch.** Repeat until complete or until the design is clearly fully
     fetched. If `maxOutputLength` reaches 2000000 and still truncates, report
     the issue to the user.

6. Persist to cache (validates + saves in one command):
   ```bash
   python <skill-dir>/scripts/cache_dsl.py save --file-id <extracted-file-id> --layer-id <extracted-layer-id> --version <version-from-getMeta> --input-file {workspace}/.cache/tac-ux-mastergo/dsl_raw_{layer_id}.json --validate-first
   ```
   Use the trimmed DSL from the cache save output as input for step 1.

7. Proceed to step 1 with the trimmed DSL as input.

**Multiple links** (user provides a list of links, a file containing links, or
pastes several MasterGo URLs):

1. Run the link inventory script to produce a navigation table on stdout:
   ```bash
   python <skill-dir>/scripts/intake_layer_inventory.py parse --links <link-list-file>
   ```
   If links are pasted in chat rather than in a file, write them to a temporary
   file first. The script emits the table between `---INVENTORY_TABLE_START---`
   and `---INVENTORY_TABLE_END---` markers.

2. Write `ux_handoff_index.md` using `templates/ux_handoff_index.md` with the
   emitted navigation table as the starting point. Present it to the user. Ask the user to:
   - Confirm which items should be analyzed (remove out-of-scope items)
   - Correct any misclassified types
   - Identify dependencies between items (e.g., which pages depend on which
     global rules)

3. Wait for user confirmation before proceeding. Do not start analysis until
   the index is confirmed.

4. After confirmation, for each item in the confirmed index, before fetching
   DSL with `mcp__getDsl`:

   a. Call `mcp__getMeta` with the item's `fileId` and `layerId` to get the
      current version. Use the returned version string as `<version>` below.

   b. Check the local cache:
      ```bash
      python <skill-dir>/scripts/cache_dsl.py check --file-id <id> --layer-id <id> --version <version>
      ```
      - `hit` → read the trimmed file at `TRIM_PATH` directly, skip MCP fetch
      - `miss` or `stale` → fetch via `mcp__getDsl` with `maxOutputLength=500000`

   c. **Truncation check** — after fetching, validate before caching:

      **Step c1 — Write raw DSL to disk:**
      Use `write_to_file` to save the MCP response JSON to:
      ```
      {workspace}/.cache/tac-ux-mastergo/dsl_raw_{item_layer_id}.json
      ```

      **Step c2 — Validate:**
      ```bash
      python <skill-dir>/scripts/cache_dsl.py validate-truncation --input-file {workspace}/.cache/tac-ux-mastergo/dsl_raw_{item_layer_id}.json
      ```
      If `truncated` or `suspicious` → double `maxOutputLength` and re-fetch.
      Once `complete` → persist:
      ```bash
      python <skill-dir>/scripts/cache_dsl.py save --file-id <id> --layer-id <id> --version <version> --input-file {workspace}/.cache/tac-ux-mastergo/dsl_raw_{item_layer_id}.json --validate-first
      ```

5. Proceed to step 1 with the trimmed DSL as input, repeating for each
   confirmed index item. Update `ux_handoff_index.md` progressively: mark
   each item's analysis status, add coverage notes, and populate the
   global/cross-page index section as rules are extracted.

> **Windows / PowerShell 适配说明：**
> 本项目 Windows 环境使用 PowerShell (Core)。以下约束必须遵守：
> - **禁止 Unix 管道语法**：`cat <file> | script.py` 在 PowerShell 中行为与
>   Bash 不同。始终使用 `--input-file` 参数传文件路径。
> - **禁止 `/tmp/` 路径**：Windows 无此目录。所有临时/缓存文件统一写入
>   `{workspace}/.cache/tac-ux-mastergo/`。
> - **DSL 写入方式**：MCP `mcp__getDsl` 返回的 JSON 在对话上下文中，须通过
>   `write_to_file` 落盘后再用 `--input-file` 传给脚本。不要尝试管道。

### 1. Gate And Inventory

Run or apply the input gate:

```bash
python <skill-dir>/scripts/validate_ux_gate.py input --mode A --has-new-truth-source <true|false> --has-existing-handoff <true|false> --target-identifiable <true|false>
```

Stop if no new interaction/business truth source or no identifiable target is
available.

Classify each input as `business-source`, `interaction-source`,
`visual-source`, `architecture-source`, or deferred `code-reference`.

Keep evidence layers separate: `interaction fact`, `visual evidence`, and
`implementation suggestion`.

### 2. Define Semantics And Ownership

Before extracting events, identify:

- page or flow purpose
- business module and actor
- entry and exit points
- correct data source and forbidden data sources
- page-owned, host-owned, shared, and global responsibilities

If one MasterGo layer contains multiple pages, popups, global flows, or
secondary pages, split rules by true owner. Do not infer final page boundaries
from `layer_id` alone.

Before detailed rule extraction, perform a whole-board semantic sweep when the
target is a long explanation board, mixed canvas, or multi-state composite:

- scan top-to-bottom and left-to-right for section titles, group names,
  annotations, state labels, and repeated carrier blocks
- list all page-local sub-scenarios explicitly, such as default state,
  history state, result state, empty state, popup state, or secondary page
- record which sub-scenarios belong to the same page and which belong to
  different pages or shared/global flows

Do not start from only the most obvious cards, inputs, or example blocks. If a
sub-scenario is present in the interaction source, it must either be modeled in
the handoff or explicitly listed as out-of-scope with a source-backed reason.

### Full-Board TEXT Node Sweep

After the whole-board semantic sweep, when the target is a long explanation board
or mixed canvas (5760×8702+), perform an explicit TEXT-node sweep against the
trimmed DSL to catch any annotation text that may be in non-obvious visual regions:

1. **Enumerate every TEXT node** in the trimmed DSL and group by coordinate region:
   - `x: 0–2560, y: relevant` → left design explanation / mockup area
   - `x: 2560–5760, y: relevant` → right flowchart / annotation / callout area
   - Any text at `x > 2560` is the most commonly missed region.

2. **Classify each TEXT node**:
   - `interaction-fact`: behavior rules, branch labels, status annotations, global
     consistency constraints (e.g. "点击btn，全应用内同一应用btn状态一致")
   - `visual-evidence`: color/font/size hints (ignore for behavior extraction)
   - `design-heading`: section titles (use for navigation, not for rules)
   - `out-of-scope`: watermark, copyright, irrelevant labels (mark explicitly)

3. **Cross-reference after rule extraction** (§3–§4):
   - Every TEXT node classified as `interaction-fact` MUST have a corresponding
     rule in §4, or an explicit "不入规则" justification in the handoff.
   - If a TEXT node appears in a flowchart region (connected to Path/arrow nodes,
     near FRAME mockup instances), it carries interaction semantics and must be
     treated as confirmed behavior evidence unless directly contradicted.

4. **Record coverage** in §0 变更记录:
   - Count of TEXT nodes scanned, count classified as interaction-fact, count
     with corresponding rules, and count intentionally excluded.
   - If any interaction-fact TEXT node has no corresponding rule, flag it as a
     `pre-blocking` pending item.

For global/shared targets, keep only shared protocols, state semantics,
cross-page synchronization, recovery rules, and forbidden page-private
divergence. Page entry UI, empty-state copy, local layout, local filtering,
management controls, and page-private visual behavior stay in page handoffs
unless explicit evidence says otherwise.

### Same-Name Variant Detection

After the whole-board semantic sweep, compare same-named FRAME or GROUP nodes:

1. Collect all FRAME/GROUP nodes that share the same `name`.
2. For each group of same-named nodes, compare their direct `children` structures
   (child count, child types, child names, component references).
3. If structural differences exist (different child composition, different
   INSTANCE componentIds, different text labels):
   - Mark them as **variants** — do not merge into a single object or state.
   - Model each variant as a separate sub-state or add a dedicated row in
     §6.3 Feedback Copy Inventory for variant-specific text.
   - Add a pending item if the variant difference affects behavior (e.g.,
     one variant has extra prompt text that changes the interaction flow).
4. If no structural differences exist beyond coordinates/visuals, the nodes
   can be treated as visual duplicates and modeled once.

### Global/Cross-Page Promotion Checklist

Promote a rule to `shared` or `global` only when evidence supports at least one
of these conditions:

- Multiple pages or flows consume the same behavior.
- The rule defines a shared protocol, long-running task, queue, recovery,
  synchronization, permission, account, network, or host-collaboration
  mechanism.
- A page can only consume or display the result and must not redefine the
  protocol privately.
- Divergent page-local behavior would break cross-page consistency, state
  recovery, acceptance, or shared implementation.

Do not promote these by default:

- entry placement, local copy, local layout, local filtering, local management
  controls, page-private visual behavior, or one-page-only display choices
- visual similarity without shared behavior evidence
- current-code reuse convenience without interaction/business evidence

If the rule may be cross-page but evidence is insufficient, add it to
`全局/跨页规则` as `candidate` or `pending`, and add an ownership confirmation
item. Do not mark it confirmed global truth.

### 3. Extract Rules

Extract behavior from annotations, node names, notes, diagrams, and requirement
text:

- click, focus, back, keyboard, remote-control, swipe, and gesture behavior
- state changes, guards, display conditions, and side effects
- ordering, grouping, filtering, refresh, limits, and persistence
- loading, empty, error, offline, disabled, permission, retry, and recovery
- toast, dialog, popup, confirmation, cancel, navigation, and host collaboration
- visible feedback copy, including toast text, black prompt bubbles, error
  tips, branch labels, disabled reasons, success/failure messages, and
  empty-state text

Separate display examples from real constraints. If a value is not explicitly
mandatory and changing it would not alter behavior, state, guard, effect, or
acceptance, treat it as an example. If still uncertain, mark it pending.

When annotated text labels that name a target page (e.g. "下载管理页",
"更新管理页", "二级页") appear **alongside visual connection lines (Path
nodes)** pointing to the same interaction object in the same DSL region,
treat the navigation relationship as **confirmed** navigation evidence — not
as pending visual evidence. The annotated text label carries interaction
semantics that make the connection an `interaction-fact`. Do not
force-confirm such navigation targets in §15 待确认项 when the DSL already
provides them.

For every visible feedback copy, create a row in either the business rules,
effect model, transition table, or boundary-state matrix. Preserve the text
verbatim and bind it to the exact trigger and guard. If several feedback
messages appear near one decision node, enumerate each one separately; do not
summarize them as a single generic failure prompt.

### Button State Labels as Feedback Copy

Button and control labels that change based on state are also first-class
feedback copy. For any interactive control whose visible label varies across
states (e.g., a button that reads different text in idle / active / completed /
failed / disabled states):

- Each distinct label variant MUST appear in §6.3 Feedback Copy Inventory, bound
  to its trigger event and guard condition.
- Progress or status indicators rendered as part of a control label (e.g.,
  percentage text, count text) MUST be extracted as variants tied to the
  corresponding update event.
- If a control has a multi-step lifecycle with different labels per step, extract
  every variant; do not collapse them into a single generic description.

**Self-check**: After scanning the DSL, enumerate all unique control label
variants visible in state annotations or transition branches. Verify each
variant appears in §6.3 with a trigger event, guard condition, and source
reference.

If the whole-board semantic sweep identified multiple sub-scenarios on the same
page, extract rules for each sub-scenario before merging them into a single
page-level state model. Do not let one sub-scenario (for example, result state)
erase another confirmed sub-scenario (for example, history state).

Write key rules in trigger-condition-result form.

### Rule Granularity Constraint

Each rule MUST represent a single trigger-condition-result triplet. Split compound
rules when:

- Multiple distinct user actions belong to one interaction object (e.g., a
  dialog with "show → toggle → confirm → cancel" is 4 separate rules,
  not 1 combined rule).

- A rule involves multiple decision branches with different conditions. Each
  branch with a distinct guard condition must be its own rule.

- A rule combines multiple state transitions under one description. Each
  source→target transition with a unique trigger must be a separate rule.

**Self-check**: After extraction, verify that no rule description contains more
than one distinct user action (click, toggle, swipe, long-press, etc.) or more
than one `→` connecting distinct outcomes. If a rule describes a multi-step
interaction flow, split it into individual trigger-condition-result rules.

### 4. Restore Diagrams When Warranted

Run scenario detection against the trimmed DSL before deciding whether to
generate a Mermaid diagram:

- **Must generate** (`decision_count >= 2` AND `branch_pair_count >= 2`):
  DSL contains clear flowchart decision nodes (e.g. "是否有网？" +
  paired "是"/"否" branches). **MUST generate a Mermaid stateDiagram**
  covering all states, transitions, guard conditions, and visible feedback
  text from the DSL.

- **Should generate** (`state_variant_count >= 1` AND `recovery_path_count >= 1`):
  DSL contains state variants or recovery paths. **SHOULD generate a
  Mermaid stateDiagram** — the topological view helps verify dead-end and
  orphan states that text tables cannot catch.

- **Skip Mermaid**: Neither condition is met. Record the skip reason in
  §0 变更记录 (Reason: `skill-analysis-enrichment`, summary: "场景复杂度
  不满足 Mermaid 生成条件").

When generating, preserve every decision branch label, visible feedback text,
and guard condition from the DSL. The Mermaid diagram must be
cross-referenced with §7 状态转移表 — the table is the truth source for
individual transitions; the Mermaid provides topological verification.

**Self-check**: After generating, run `validate_ux_handoff.py --dsl <trimmed-dsl>`.
The validator checks Mermaid syntax (T1), node-set consistency (T2), and
reachability (T3 — WARN only).

### 4.5 Self-Check Gate (MANDATORY Before §5)

**This gate cannot be skipped.** Before writing any §5 content, perform and
record these checks explicitly:

**Checklist:**

- [ ] Scanned trimmed DSL for `?` decision nodes → found __
- [ ] Scanned trimmed DSL for `是` / `否` branch labels → found __ pairs
- [ ] Scanned trimmed DSL for state variants & recovery paths → variants __, recovery paths __
- [ ] Decision: **[ MUST generate / SHOULD generate / SKIP ]**

**Decision logic:**

| Condition | Verdict | Action |
|:--|:--|:--|
| `decision_count ≥ 2 AND branch_pair_count ≥ 2` | **MUST** | Generate Mermaid **before** §5 |
| `state_variant_count ≥ 1 AND recovery_path_count ≥ 1` | **SHOULD** | Generate Mermaid **before** §5 |
| Neither satisfied | **SKIP** | Record reason in §0 |

**If MUST or SHOULD → generate the Mermaid stateDiagram NOW, before writing §5.**
The Mermaid diagram provides topological verification (dead-end states, orphan
states, unreachable transitions) that text tables cannot catch.

**Record the decision** in §0 变更记录 regardless of outcome:
- Generating: `skill-analysis-enrichment` summary: "DSL检测到 N 决策节点 + M 配对分支 → MUST/SHOULD 生成 Mermaid stateDiagram"
- Skipping: `skill-analysis-enrichment` summary: "场景复杂度不满足 Mermaid 生成条件 (decision_count=N, branch_pair_count=M)"

### 5. Build Implementation-Ready Models

Create:

- state list with meaning, required data, and UI obligation
- event/intent list with trigger source, preconditions, and payload
- effect list for navigation, feedback, request, persistence, analytics, or host
  communication
- transition table
- boundary-state matrix
- global/shared rule extraction result
- feedback copy inventory when the source contains any visible prompt/toast or
  inline error/success message

Use stable names that can be copied into code. Preserve them across later
updates unless evidence or user confirmation requires change.

### Sub-Component State Scan

After building the page-level state model and the primary interaction object state
model (e.g., action-button state machine), for every interaction object listed in
§3, scan whether it has **independently visible states**:

1. Check whether the object presents ≥2 distinct visible configurations that
   change based on data, user action, or system state. Generic patterns that
   typically warrant sub-state models include:
   - Cards with dynamic indicators: with/without count or status badges,
     normal/alert variant
   - Carousel or gallery components: single-item vs multi-item mode, auto-scroll
     vs manual
   - Multi-option selectors (tabs, segments, chips): selected/unselected
     per-option state, disabled state
   - List items: default/selected/disabled/expanded configurations
   - Any component annotated in DSL with alternate states (empty, loading, error,
     different copy variants, mode-switching layouts)

2. For each object with ≥2 distinct visible configurations:
   - Add a sub-state group under §5, with a stable name, meaning, required data,
     display obligation, triggerable events, and source evidence.
   - Cross-reference its trigger events and transitions in the transition table.

3. If an interaction object has only one configuration or its visible change is
   purely cosmetic (color, size, spacing without semantic meaning), mark it
   explicitly as "no independent state" to signal that omission is intentional.

**Self-check**: Count interaction objects in §3 and sub-state groups in §5.
Verify that every object with ≥2 visible configurations appears as a sub-state
group, or is explicitly marked as "no independent state".

### 6. Generate The Handoff(s)

Use `templates/ux_handoff.md` as the template for each behavior contract.

**Output structure — single entity at a time, index always present:**

```text
{user-specified output directory}/
├── ux_handoff_index.md            # 导航 + 覆盖 + 全局索引
├── ux_handoff_{page-or-flow}.md   # 页面/流程 handoff
├── ux_handoff_global_{topic}.md   # 复杂全局规则（可选）
└── ...
```

> **产物结构、全局规则拆分、`{name}` 命名均以 SKILL.md「Output Contract」为准。**
> 简要提示：简单全局规则在 index 内联展开，复杂规则独立 `ux_handoff_global_{topic}.md`；
> `{name}` 推导 → DSL 节点名 → 类型判断 → 去重消歧 → snake_case；
> `{topic}` 命名同 snake_case，示例：`download_button`、`payment_flow`（非 `*_shared` 后缀）。

When whole-board sweep identifies multiple entities in a single DSL, produce one
handoff per entity, not one combined file. Write `ux_handoff_index.md` first (or
update its navigation table if it already exists), then produce individual
handoffs, updating the index's status as you go.

#### 6.0 Index Merge Protocol (MANDATORY before writing Index)

**CRITICAL**: Multiple AI sessions may run Mode A in parallel on different
MasterGo layers. Each session MUST merge its entries into the shared Index
rather than overwriting it. `write_to_file` on `ux_handoff_index.md` is
FORBIDDEN when the file already exists.

**Protocol — run BEFORE writing Index:**

1. **Check if Index exists** by reading the output directory:
   - If `ux_handoff_index.md` does NOT exist → write it fresh (first session)
   - If `ux_handoff_index.md` EXISTS → **MUST merge**, do NOT overwrite

2. **When Index exists, merge via diff report:**
   ```bash
   # Step a: Write incoming (current session) index to a temp file
   # (write your new index entries to <output-dir>/ux_handoff_index_incoming.md)

   # Step b: Run merge diff
   python <skill-dir>/scripts/intake_layer_inventory.py merge \
     --existing <output-dir>/ux_handoff_index.md \
     --incoming <output-dir>/ux_handoff_index_incoming.md
   ```

3. **Apply the merge report** emitted by the script:
   - **New entries** (`§1/§2/§3 — New entries to ADD`): use `replace_in_file` on
     the existing `ux_handoff_index.md` to append new rows to the relevant tables
   - **Updated entries** (`Entries to UPDATE`): use `replace_in_file` to update
     specific rows (incoming wins for §1 编号 and §3 编号; existing wins for §2)
   - **Already present**: skip

4. **Deduplication rules:**
   - §1 (交互稿清单): deduplicate by `编号`; incoming wins (newer session status)
   - §2 (全局/跨页规则): deduplicate by `规则摘要` (exact match); existing wins
   - §3 (待确认项): deduplicate by `编号`; incoming wins (newer session status)

5. **Clean up**: delete `ux_handoff_index_incoming.md` after merge is applied

6. **Validate**: after merge, run:
   ```bash
   python <skill-dir>/scripts/intake_layer_inventory.py validate --index <output-dir>/ux_handoff_index.md
   ```
   The validator now performs cross-checks: unregistered handoff files in the
   directory will be flagged as ERROR.

> **Why this matters**: In January 2026, 5 parallel sessions generated Index
> files that overwrote each other, resulting in only the last session's entries
> surviving. The merge protocol prevents this permanently.

For confirmed rules, include source traceability, evidence layer, ownership, and
confidence. For visual input, include UI coordination but avoid pixel-perfect
details. Without visual input, include provisional skeleton guidance and mark UI
structure gaps.

Review unresolved items with the interruption gate:

```bash
python <skill-dir>/scripts/validate_ux_gate.py interrupt --has-pre-blocking <true|false> --has-blocking <true|false> --has-non-blocking <true|false> --resume-point <checkpoint>
```

Save a checkpoint before pausing for confirmation.

Do not defer confirmation behind warning cleanup or formatting polish. After
the handoff is generated, check `待确认项` immediately:

- any `pre-blocking` item => pause now
- any `blocking` item => pause before any further implementation planning
- only `non-blocking` items may be carried forward

Treat this as a separate confirmation gate from validator pass/fail. A
validator `PASS` means the handoff is structurally valid; it does not mean the
workflow may continue.

### 6.5 Optional: Resolve Conflicts with PRD / Requirements Document

When `待确认项` contains `pre-blocking` or `blocking` items whose resolution
could change behavior, ownership, or acceptance, attempt to resolve them using a
requirements document before pausing for user input.

**Auto-search (do not ask user first):**

1. Search the project for requirements/PRD documents:
   - `PROJECT.md`, `AGENTS.md` — project-level context
   - `specs/**/*.md` — feature specs / design docs
   - `doc/**/*.md`, `docs/**/*.md` — design documents
   - Files containing keywords: `PRD`, `需求`, `requirement`, `spec`, `设计`, `验收`

2. If one or more candidate documents are found, load the most relevant one(s)
   and attempt to resolve pending items:
   - Use PRD evidence to confirm or correct ownership decisions
   - Use PRD evidence to disambiguate behavior, state, or data expectations
   - Update the handoff with resolved items, citing the PRD as
     `requirement-source`

3. If no requirements document is found, or if the found document does not
   contain enough evidence to resolve the items:
   - Prompt the user: "当前存在 X 个待确认项，未在项目中找到需求文档。是否提供 PRD/需求文档辅助消解？"
   - Wait for user response before proceeding

Do not treat PRD as a substitute for interaction evidence. When PRD and
interaction source conflict, mark the conflict explicitly and ask the user to
resolve; do not silently prefer one source.

### 6.6 Developer Triage And Confirmation Routing

After PRD conflict resolution (6.5), if `待确认项` still contains `blocking` or
`pre-blocking` items, run the **developer triage** before pausing the session:

1. **Present all blocking/pre-blocking items** with AI-suggested `确认角色`
   (product / interaction / visual / technical / host / data / mixed).

2. **Developer triages each item** one by one:
   - Items the developer can confirm immediately → resolve in-session, update
     handoff `待确认项` status.
   - Items that need PM/UX/visual confirmation → mark as deferred.
   - Developer may re-route items (e.g., change role from technical to product)
     at this point.

   **After triage, write triage results back to the handoff file before
   proceeding.** For each item:

   - **Resolved in-session**: in handoff §15, strikethrough the `阻塞级别`
     value (e.g. `~~blocking~~`), append `→ resolved` and the resolution note.
     **ALSO add a row to §0.2 交互更新记录** with `Change ID` (`CONF-NNN`,
     incrementing from the last used number), `Type` (`clarified`), `Source`
     (`developer-confirmation`), the previous pending question and new resolution,
     and `Affected sections` listing `§15` plus any sections whose content
     changed as a result. This ensures a centralized, time-sequenced audit trail
     of all confirmation decisions.
   - **Deferred for external confirmation**: if the current `阻塞级别` is
     `non-blocking`, upgrade it to `blocking` to ensure
     `gen_confirmation_sheet.py` picks it up. The script filters by blocking
     level; non-blocking items are excluded from the xlsx by default.

   > ⚠️ The confirmation sheet generator reads the handoff file from disk.
   > Triage conclusions that exist only in memory will be lost.
   > **You MUST update the handoff §15 AND §0.2 on disk before running the script.**

3. **Generate external confirmation sheet** for deferred items only:

   ```bash
   python <skill-dir>/scripts/gen_confirmation_sheet.py --handoff-dir <output-dir>
   ```

   This produces `ux_confirmation_sheet.xlsx` following
   `templates/ux_confirmation_sheet_spec.md` — one Sheet per role, color-coded
   by blocking level, metadata in Sheet 0 for self-indexed replay.

4. **Developer reviews the xlsx** before sending to external stakeholders.
   The developer may directly edit the xlsx (add/remove/change rows) in Excel.

5. **Add a replay hint** to `ux_handoff_index.md` §3 待确认项汇总, above the
   table:

   ```
   > ⚠️ 当前存在 N 项待外部确认（见 ux_confirmation_sheet.xlsx）。
   > 确认单回传后，对 AI 说「回放UX确认单」即可自动更新。
   ```

6. **Record Resume Point** and report to the user:
   - Items confirmed in-session (count)
   - Items deferred to confirmation sheet (count by role)
   - Path to `ux_confirmation_sheet.xlsx`
   - **Do not block the current session** — the developer may proceed with
     steps 7-8 (code conflict check, final validation) on non-blocking items
     while waiting for external confirmation.

### 6.7 Confirmation Replay

When the developer returns (same session or new session) with a filled
`ux_confirmation_sheet.xlsx`, replay the conclusions into the handoffs:

1. **Run the replay script:**

   ```bash
   python <skill-dir>/scripts/replay_confirmation.py \
     --xlsx-dir <output-dir> \
     --handoff-dir <output-dir>
   ```

   The script scans all `ux_confirmation_sheet*.xlsx` in the directory,
   merges findings, and outputs five categories:

   ```
   adopted     — new conclusions, ready to write into handoff
   revised     — existing conclusion changed, needs developer review
   unchanged   — unchanged, already in handoff
   conflict    — same item, different conclusions across xlsx files
   unresolved  — conclusion column still empty
   ```

2. **AI processes each category:**
   - **adopted**: Write conclusions into the corresponding handoff §15 待确认项
     row (update `阻塞级别` and add resolution note).
   - **revised**: Present each item to the developer for review. Developer
     decides whether to accept the revision or keep the original.
   - **conflict**: Present conflict details to the developer for resolution.
     The developer is the final arbiter — do not auto-resolve conflicts.
   - **unchanged**: No action needed. Report for awareness.
   - **unresolved**: Keep the original blocking level. These items are still
     waiting for external input.

3. **After all updates**, re-run the interruption gate:

   ```bash
   python <skill-dir>/scripts/validate_ux_gate.py interrupt \
     --has-pre-blocking <true|false> --has-blocking <true|false> \
     --has-non-blocking <true|false> --resume-point confirmation-replay
   ```

4. If gate passes → continue with Step 7 (code conflict check) and Step 8
   (final validation). If items remain unresolved → suggest keeping the xlsx
   for another round; do not delete it.

**Replay is idempotent**: the script can be run multiple times. Already-applied
items are detected by comparing xlsx conclusions against handoff status and
reported as `unchanged` or `revised`.

### 7. Optional Code Conflict Check

Only after the handoff is complete and the user requests conflict/readiness
checking, inspect provided code paths. Classify code as implemented, missing,
wrong, conflicting, reusable, or needs confirmation. If code suggests a possible
missing rule, record it as a question, not as design fact.

## Validation And Final Output

Validate all saved handoffs and index: → see SKILL.md「Validation」for the exact commands.

Then report, in order:

1. index path (`ux_handoff_index.md`)
2. handoff paths (one per entity, plus optional global)
3. mode
4. validation result (`PASS` / `FAIL`) — index + each handoff
5. coverage summary (from index)
6. execution readiness (`ready` / `pause-for-confirmation`)
7. blocking/pre-blocking confirmation items, if any
8. input gaps
9. optional conflict-check status
10. 1 to 3 suggested next steps

Include `Resume Point` whenever paused for confirmation.
