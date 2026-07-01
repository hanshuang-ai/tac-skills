# Capability Registry & Blind-Spot Audit

> 定位：本文件是 `tac-ux-mastergo` 技能的跨版本能力登记表、盲区审计记录和退化检测规则。
> 由 Skill 维护者在首次产生跨版本对比时建立，后续迭代持续更新。
> 不参与产物输出，仅供 Skill 迭代治理使用。

---

## 1. 能力登记表

> 能力 = Skill 预期输出的核心质量维度（非具体字段名）。

| # | 能力 | 定义 | 退化检测方式 | 当前状态 |
|:--|:--|:--|:--|:--|
| C1 | 规则粒度强制 | 每条业务规则仅含单个 trigger-condition-result 三元组，不含复合动作 | `validate_rule_granularity()` — 检测多 `→` 箭头 / 多动作动词 | ✅ 生效 |
| C2 | 子组件状态建模 | 含 ≥2 种可见形态的交互对象在 §5 建立子状态组，或显式标注 "no independent state" | `validate_sub_component_coverage()` — §3 对象数 vs §5 子状态组数比率 ≥ 0.5 | ✅ 生效 |
| C3 | 反馈文案逐条提取 | toast / prompt / error / success / empty / button-label 文案逐条录入 §6.3，绑定触发事件+Guard | `validate_feedback_copy()` — 反馈类型覆盖度 + DSL 文本节点覆盖率 | ✅ 生效 |
| C4 | 业务规则来源追溯 | confirmed 规则必须填 source type + source location，禁止 code-reference 作为业务证据 | `validate_business_rules()` — source_type 非空 + 值域检查 | ✅ 生效 |
| C5 | 归属冲突检测 | ownership-conflict 规则须在 §15 有对应待确认项；全局 handoff 不接受 page-local 规则 | `validate_page_global_ownership()` — 跨节一致性与归属合理性 | ✅ 生效 |
| C6 | 变更审计记录 | §0.2 交互更新记录在确认决策和每次维护后写入变更行，与 §15 resolved 交叉一致 | `validate_change_record()` — §15 有 ~~resolved~~ 但 §0.2 无对应行时报错 | ✅ 生效 |
| C7 | 状态图还原 | 输入含 flowchart/状态图时产出结构化 Mermaid 图 | `validate_mermaid_syntax()` T1+T2 ERROR; `validate_mermaid_reachability()` T3 WARN; `validate_mermaid_should_exist()` 场景检测 WARN | ✅ 生效 |
| C8 | 确认单生成与回放 | blocking/pre-blocking 待确认项生成 xlsx，回传后通过 replay 脚本写回 handoff | `gen_confirmation_sheet.py` + `replay_confirmation.py` 功能正确性 | ✅ 功能存在 |
| C9 | 多链接盘点 | 多个 MasterGo 链接时 emit 导航表，去重，确认范围后再分析 | `intake_layer_inventory.py parse` + `validate` | ✅ 生效 |
| C10 | DSL 缓存与裁剪 | 版本命中时复用本地 trimmed DSL，避免重复 MCP fetch | `cache_dsl.py check/save` — hit/miss/stale 三态 | ✅ 生效 |
| C11 | DSL 截断检测 | `mcp__getDsl` 后验证 JSON 完整性和结构完整性，截断时自动翻倍 maxOutputLength 重试 | `cache_dsl.py validate-truncation` — JSON parse + structural integrity check | ✅ 生效 |
| C12 | 全量文本标注扫描 | 大画板混合 canvas 的 DSL 提取时对**所有 TEXT 节点**做区域扫描（左/右/底部），不依赖"设计说明"标题定位；流程图侧标、连线旁标注等非标题区文本视为一等交互证据 | Mode A §2 Full-Board TEXT Node Sweep 自检 + §4 交叉校验 | ✅ 生效 |

---

## 2. 盲区审计

> 每次迭代前更新，记录已知 validator 缺口和"刻意不改"项。

### 当前版本盲区（2026-05-22 审计）

| 遗留盲区 | 发现于 | 当前状态 | 说明 |
|:--|:--|:--|:--|
| C7 状态图还原无 validator | 首次审计 | 刻意不改 | Mermaid 代码块的结构化校验较复杂，当前依赖人工 review；若误检率高暂不脚本化 |
| C6 变更记录仅检查 §15→§0.2 的回写一致性，不检查变更描述本身的语义完整性 | 首次审计 | 刻意不改 | 语义完整性（如 "是否描述了影响范围"）属于自然语言判断，放到 validator 中误报风险过高 |
| C2 子组件覆盖的阈值 0.5 为经验值，可能对页面数少的 handoff 过于宽松 | bench_20260522 | 刻意不改 | 当前 0.5 阈值下未观察到漏检；如有误判再调整 |
| 全局规则 handoff 中误迁入页面私有行为，validator 仅做关键词匹配检测（`global/shared/跨页`），可能漏检 | 首次审计 | 不修 | 全局 handoff 的判断依赖上下文语义；当前关键词 probes 已覆盖大多数场景 |
| bench_iteration.py L1 quick mode 的 HEAD vs HEAD 自比较无意义（必然无 diff） | bench_20260522 | 不修 | L5 test_l5() 中已将此降级为 WARN，不影响整体 gate |
| `templates/` 中多选项决策树缺少内联注释 | 2026-05-26 治理审查 | ✅ 已修复 | `ux_handoff.md` §0 已新增 Reason 五选项决策树内联注释 |
| E1 Mermaid 场景检测与语法校验缺失 | 2026-05-26 | ✅ 已修复 | T1+T2 纯机械校验（regex+集合运算，零误检）；T3 WARN 标注"需人工判断"；场景检测决定是否触发 |
| E2 INSTANCE 组件文本穿透缺失 | 2026-05-26 | ✅ 已修复 | 检测 trimmed DSL 中 INSTANCE 节点的未解析文本（componentId 引用但无实际文案），发 WARN 提醒 |
| E3 全局 Handoff 消费页面证据缺失 | 2026-05-26 | ⚠️ 模板级别修复 | `ux_handoff.md` 全局 Handoff §11 模板注释已更新为"消费页面证据矩阵"；无独立 validator |
| E4 同名 FRAME 变体合并风险 | 2026-05-26 | ⚠️ workflow 级别约束 | `mode_a_workflow.md` §2 新增 Same-Name Variant Detection 子步骤；无独立 validator |
| E5 DSL 截断检测缺失 | 2026-05-29 | ✅ 已修复 | 新增 `cache_dsl.py validate-truncation` + `mode_a_workflow.md` steps 4-6 + `SKILL.md` Hard Rule + C11 能力登记 |
| E6 大画板流程图区域文本遗漏 | 2026-05-29 | ✅ 已修复 | 混合 canvas（5760×8702+）右侧流程图标注区（`x > 2560`）的 TEXT 节点未被系统扫描；根因：提取依赖"设计说明"标题定位，跳过了非标题区的标注文本。修复：`SKILL.md` 新增"全量文本标注扫描"硬规则 + `mode_a_workflow.md` §2 新增 Full-Board TEXT Node Sweep 子步骤（按坐标分区 + 交叉校验）+ C12 能力登记 |

---

## 3. 退化检测规则

> 以下规则供 `references/mode_c_maintenance_workflow.md` 在保存前执行。
> 形式为自然语言约束，维护者可在 mode_c workflow 中引用本节。

### D1. 非占位符→占位符回退检查

维护前记录每节的 concrete rows 计数（非空行、非纯枚举选项行）。保存前对比：
- 若此前有 ≥1 条具体规则行，更新后变为 0 或全部为占位符（如 "待补充"），标记为潜在退化。
- 必须给出退化原因说明（"刻意删除" / "合并到其他行" / "证据失效"），否则回滚。

### D2. 已确认项→open 回退检查

检查 §15 待确认项：
- 若此前某条标记为 `~~blocking~~` / `~~pre-blocking~~` / `resolved`，更新后该行 阻塞级别 回退为 `blocking` 或 `pre-blocking`，需提供源证据证明为何此前结论失效。
- 同样适用于 §0.2 交互更新记录中 `Status: confirmed` → `Status: pending` 的回退。

### D3. 子模型/图表缺失检查

检查以下模式：
- 若旧版 §5 存在子状态组表格（≥1 个 concrete row），新版 §5 不存在任何子状态组表格 → 列出缺失项。
- 若旧版 handoff 中存在 ` ```mermaid ` 代码块，新版中消失 → 需显式说明"原始输入不含图"或"图已合并到 index"。
- 若旧版 §6.3 反馈文案清单有 ≥3 条 concrete row，新版 ≤1 条 → 标记退化，需逐条说明删除原因。

---

## 4. 能力守护清单

> 每次产能迭代的提交信息中附带此清单。

```markdown
能力守护：
  - [C1 规则粒度强制]: 守住 / 退化（原因）/ 不适用
  - [C2 子组件状态建模]: 守住 / 退化（原因）/ 不适用
  - [C3 反馈文案逐条提取]: 守住 / 退化（原因）/ 不适用
  - [C4 业务规则来源追溯]: 守住 / 退化（原因）/ 不适用
  - [C5 归属冲突检测]: 守住 / 退化（原因）/ 不适用
  - [C6 变更审计记录]: 守住 / 退化（原因）/ 不适用
  - [C7 状态图还原]: 守住 / 退化（原因）/ 不适用
  - [C8 确认单生成与回放]: 守住 / 退化（原因）/ 不适用
  - [C9 多链接盘点]: 守住 / 退化（原因）/ 不适用
  - [C10 DSL 缓存与裁剪]: 守住 / 退化（原因）/ 不适用
  - [C11 DSL 截断检测]: 守住 / 退化（原因）/ 不适用
  - [C12 全量文本标注扫描]: 守住 / 退化（原因）/ 不适用
```
