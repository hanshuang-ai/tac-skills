# Mode C Handoff Maintenance Workflow

Use only after `SKILL.md` routes the task to Mode C.

## Goal

Update an existing UX handoff without losing confirmed business rules. When no
new interaction input is provided, the existing confirmed handoff plus its
recorded evidence is the analysis baseline.

## Loading Contract

May read:

- `ux_handoff_index.md` (navigation and scope)
- `templates/ux_handoff_index.md` (index structure)
- existing UX handoff(s)
- `templates/ux_handoff.md`
- `scripts/validate_ux_gate.py`
- `scripts/validate_ux_handoff.py`
- `scripts/intake_layer_inventory.py` (index validation)
- changed or unchanged source artifacts needed for this maintenance pass

Must not read production code unless the user explicitly asks for a conflict
recheck. Must not treat code as behavior evidence.

## 1. Classify Maintenance

Choose one reason before editing:

- `interaction-design-update`: interaction, requirement, visual, architecture,
  or explicit confirmation input changed.
- `skill-structural-upgrade`: input did not change; structure, template,
  checker, or quality bar changed.
- `skill-analysis-enrichment`: input did not change; the upgraded skill can
  extract more precise constraints, states, transitions, acceptance items, or
  pending questions from existing evidence.
- `mixed`: multiple reasons apply.

Record:

| Field | Value |
|:--|:--|
| Maintenance reason | interaction-design-update / skill-structural-upgrade / skill-analysis-enrichment / mixed |
| Business rules changed? | yes/no/unknown |
| New design inputs provided? | yes/no |
| Existing inputs reanalyzed? | yes/no |
| Code conflict recheck requested? | yes/no |
| Target update style | local patch / template migration / analysis enrichment / validation repair |

Validate the entry:

```bash
python <skill-dir>/scripts/validate_ux_gate.py input --mode C --has-new-truth-source <true|false> --has-existing-handoff <true|false> --target-identifiable <true|false>
```

Stop if the existing handoff is missing or the requested truth source is
unavailable. If business-rule change is `unknown`, ask before changing confirmed
rules.

## 2. Inventory Existing Handoff

If `ux_handoff_index.md` exists, use its navigation table to identify which
handoff files to load. Each handoff is inventoried independently.

For each handoff and the index, identify:

- confirmed rules and source evidence
- pending questions
- missing or stale template sections
- validation failures
- stable downstream contract names
- global/shared rules and page-local rules
- prior conflict-check results
- Mermaid diagram presence: does `` ```mermaid `` exist? If missing, does §7
  状态转移表 have ≥3 state variants with recovery/branch keywords? This
  triggers `skill-analysis-enrichment` — see §3. If `--dsl` is available for
  the original interaction source, run `validate_ux_handoff.py --dsl <path>`
  for authoritative flowchart detection.

Preserve stable semantic, state, event, effect, rule, and ownership names unless
the user confirms a rename or evidence proves the old name wrong.

For global/shared handoffs, keep page-local behavior only as references to the
owning page handoff or mark ownership conflict. Do not leave page-private
behavior as confirmed global truth.

If the existing handoff is a single combined file (pre-multi-file upgrade),
consider whether splitting into `ux_handoff_{name}.md` files + index is
appropriate. Classify this as `skill-structural-upgrade`.

### 2.5 Optional: Resolve Conflicts with PRD / Requirements Document

When maintenance surfaces `pre-blocking` or `blocking` items, ownership
conflicts, or ambiguous rules, follow the **same PRD conflict-resolution
procedure as Mode A Step 6.5**: auto-search the project for requirements
documents, attempt resolution using PRD evidence (citing as
`requirement-source`), and prompt the user if no document is found or
evidence is insufficient. Do not let PRD silently override confirmed
interaction evidence.

> For the full procedure (search paths, resolution logic, conflict rules),
> see `references/mode_a_workflow.md` Step 6.5.

### Global/Cross-Page Maintenance Checklist

During maintenance, recheck global/shared ownership before changing confirmed
rules:

- If a confirmed global rule is actually entry UI, local copy, layout, local
  filtering, local management control, or page-private visual behavior, move it
  back to the owning page handoff or mark `ownership-conflict`.
- If an existing page rule clearly defines shared protocol, cross-page state,
  recovery, synchronization, permission, account, network, queue, or host
  collaboration behavior, add it to `全局/跨页规则` with source evidence and
  status.
- If interaction input did not change, classify ownership correction as
  `skill-analysis-enrichment` unless it only repairs structure.
- If evidence is insufficient, keep the rule as `candidate` or `pending`; do not
  convert it into confirmed global truth.
- If code shows reuse but source evidence does not, record a conflict or
  implementation suggestion, not a business rule.

For every global/shared update, verify `影响范围`, `当前页消费方式`, `归属建议`,
`状态`, and `来源`. If any field cannot be filled from evidence, the rule is not
ready to be confirmed.

### 2.6 Snapshot Baseline for Degradation Detection

Before applying any changes, capture a baseline of the existing handoff for
post-update comparison. Load `references/capability_registry.md` §3 for the
full degradation detection rules; apply these checks after saving:

**D1. Non-placeholder → placeholder regression:**
- Count concrete rule rows (§4), state-model rows (§5), transition rows (§7),
  feedback-copy rows (§6.3), and pending items (§15) in the pre-update handoff.
- After saving, diff against the baseline. If a section previously had ≥1
  concrete entry and the update reduces it to 0 or replaces all entries with
  placeholder/default values (`待补充`, `—`, `TBD`), flag as potential
  regression and require an explicit reason written into §0 变更记录.

**D2. Resolved → open status reversal:**
- If any pending item (§15) previously marked `~~blocking~~` / `~~pre-blocking~~`
  / `resolved` changes back to an unresolved blocking level, require source
  evidence for the status reversal. Record the reversal reason in §0.2.
- Same check applies to §0.2 rows where `Status: confirmed` reverts to
  `Status: pending`.

**D3. Sub-model / diagram absence:**
- If the pre-update handoff contained sub-state groups in §5 (≥1 concrete data
  row in a sub-state table) and the update removes them all, list the missing
  items explicitly in §0 变更记录.
- If the pre-update handoff contained a ` ```mermaid ` diagram block that is
  absent from the post-update version, state whether the diagram was
  intentionally removed, merged into `ux_handoff_index.md`, or is a
  regression.
- If the pre-update §6.3 feedback copy inventory had ≥3 concrete rows and the
  post-update version has ≤1, list each removed row and its deletion reason.

Baseline snapshots are transient — they exist only for the duration of the
maintenance session and are not saved to disk as separate artifacts. Report
degradation warnings alongside the final validation output.

## 3. Apply The Right Update Path

### Interaction/Design Update

Use only when new or changed source input exists.

Classify changes as `added`, `modified`, `deprecated`, `clarified`, or
`conflict-fix`. Update only affected sections. Record the source and update
state transitions, boundary states, and acceptance items together when behavior
changes.

For visual-completion input, update UI coordination first and state whether only
mapping changed or confirmed interaction facts also changed.

### Skill Structural Upgrade

Allowed:

- add or rename sections required by the latest template
- normalize columns and traceability
- split a combined handoff into `ux_handoff_index.md` + per-entity handoffs
  without changing behavior
- split mixed page/global structure without changing behavior
- regenerate `ux_handoff_index.md` navigation table and global index from
  existing handoff content. **WARNING**: When regenerating, follow the Index
  Merge Protocol from Mode A Step 6.0 — read existing Index first, extract
  entries from other sessions, merge instead of overwriting. Use
  `intake_layer_inventory.py merge` for deduplication.
- add empty or `待确认` placeholders where evidence is absent
- repair validation failures

Forbidden:

- changing confirmed behavior, page semantics, data source, navigation, states,
  or ownership without evidence
- inventing rules from best practice or current code
- broad style-only rewrites of unaffected sections

### Skill Analysis Enrichment

Allowed when supported by existing evidence:

- derive missing boundary states or transitions
- split broad rules into implementation-ready constraints
- recover missed visible feedback copy from existing screenshots, flowcharts,
  annotations, or state diagrams, preserving exact text and trigger conditions
- restore Mermaid stateDiagram from DSL flowchart/state evidence when the
  handoff has state variants and decision branches but no diagram. Follow
  Mode A §4 decision thresholds (Must/Should/Skip) and §4.5 self-check gate.
  Record in §0 as `skill-analysis-enrichment`
- add acceptance items for existing rules
- identify missed pending questions
- improve source traceability
- correct page/global ownership when evidence supports it

Forbidden:

- inventing behavior from general practice
- using current code as business evidence
- treating weak inference as confirmed truth
- renaming stable contract objects without evidence-backed need

Classify enrichments:

| Enrichment | Type | Previous gap | Input evidence | Conclusion level | Needs confirmation |
|:--|:--|:--|:--|:--|:--|
|  | constraint/boundary-state/state-transition/feedback-copy/acceptance/pending-question/global-rule |  |  | explicit/derived/pending/rejected | yes/no |

Only `explicit` and defensible `derived` items may update confirmed sections.
`pending` items go to `待确认项`.

When the maintenance reason is skill-analysis-enrichment, explicitly check
whether prior broad rules such as "show error", "submit failed", "offline", or
"retry" lost source-visible copy. If exact copy exists in the evidence, add it
as `feedback-copy`; if capability support is missing, keep the copy and record
the capability gap separately.

## 4. Update Change Records

Update `变更记录`, `影响矩阵`, and either `交互更新记录` or `分析增强记录`.

Use these statements when applicable:

- `本次仅按新版 tac-ux-mastergo 结构/校验要求整理产物，未改变已确认交互与业务规则。`
- `本次交互输入未变化；新增分析项均来自既有输入证据，未凭空新增业务规则。`

When no confirmed business rule changed, explicitly say downstream contract
names remain stable unless otherwise noted.

### 4.5 Handle New Blocking Items

If maintenance surfaces new `blocking` or `pre-blocking` pending items (e.g.
ownership conflicts, ambiguous rules, newly identified gaps), follow the same
confirmation routing as Mode A:

1. **Developer triage** — follow Mode A Step 6.6:
   resolve items the developer can confirm in-session; defer items needing
   external confirmation to a confirmation sheet.

2. **Generate confirmation sheet** for deferred items:
   ```bash
   python <skill-dir>/scripts/gen_confirmation_sheet.py --handoff-dir <output-dir>
   ```

3. **Confirmation replay** — follow Mode A Step 6.7 when the filled xlsx
   returns:
   ```bash
   python <skill-dir>/scripts/replay_confirmation.py --xlsx-dir <output-dir> --handoff-dir <output-dir>
   ```

> The same write-back requirement applies: update handoff §15 on disk
> before running `gen_confirmation_sheet.py`. See Mode A Step 6.6 for
> detailed triage procedure.

## 5. Validate And Stop

Validate each updated handoff:

```bash
python <skill-dir>/scripts/validate_ux_handoff.py <handoff.md>
```

If the trimmed DSL cache file is available for the original interaction source,
use `--dsl` for authoritative flowchart detection and Mermaid scene checks:

```bash
python <skill-dir>/scripts/validate_ux_handoff.py <handoff.md> --dsl <path-to-trimmed-dsl.json>
```

If `ux_handoff_index.md` was created or updated, validate the index:

```bash
python <skill-dir>/scripts/intake_layer_inventory.py validate --index <output-dir>/ux_handoff_index.md
```

> The validator now includes a cross-check (`_cross_check_directory`):
> all `ux_handoff_*.md` files in the directory are compared against Index §1/§2
> registrations. Unregistered files are reported as ERROR — this catches
> orphan handoffs from parallel sessions that were accidentally dropped from
> the Index during regeneration.

If validation fails because old structure is missing, migrate structure without
changing business rules. If evidence is missing, mark pending questions instead
of inventing rules.

Before leaving maintenance, apply the interruption gate:

```bash
python <skill-dir>/scripts/validate_ux_gate.py interrupt --has-pre-blocking <true|false> --has-blocking <true|false> --has-non-blocking <true|false> --resume-point <checkpoint>
```

Report result, maintenance reason, whether business rules changed, updated
handoff path(s) (including `ux_handoff_index.md` if changed), changed sections,
remaining pending items, validation result, and 1 to 3 suggested next steps.
Include `Resume Point` if paused. Do not proceed to implementation unless the
user explicitly asks for Mode B.
