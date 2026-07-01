# UX Handoff Index

> **生成工具**：tac-ux-mastergo v{从 SKILL.md frontmatter version 字段读取}
> **定位**：本文件是当前项目所有 UX Handoff 产物的唯一导航入口和源链接登记处。
> 源链接仅在此处记录；各 per-entity handoff 通过「链接见 index」引用，不重复粘贴。

## 0. 变更记录

| Version/Date | Reason | Summary | Source |
|:--|:--|:--|:--|
|  | initial / maintenance |  |  |

## 1. 交互稿清单与进度

> 清单由 `intake_layer_inventory.py parse` 生成草稿，经人工确认范围后固化为正式表。
> 分析过程中逐项更新「状态」「产物文件」列。

| 编号 | 名称 | MasterGo 源链接 | file_id | layer_id | 类型初判 | 是否建议纳入分析 | 状态 | 产物文件 | 依赖 | 备注 |
|:--|:--|:--|:--|:--|:--|:--|:--|:--|:--|:--|
|  |  |  |  |  | 页面 / 弹窗 / 浮层 / 半屏 / 面板 / 全局/共享规则 / 说明/文档区 | ✅ / ❌ | ⏳ pending / ✅ done / ⏭️ skipped | `ux_handoff_{name}.md` |  |  |

> **状态**：`⏳ pending`（待分析）→ `✅ done`（已生成 handoff）→ `⏭️ skipped`（已确认跳过，原因写入备注）
>
> **是否建议纳入分析** vs **状态**：前者是脚本/人工的范围初判，后者是最终执行结果。如脚本标记 ❌ 但人工确认纳入，则状态为 pending/done。

## 2. 全局/跨页规则

> **轻量规则（simple）**在此节内联展开；**复杂规则（complex）**指向独立 `ux_handoff_global_{topic}.md`。
> 判定标准：需独立实现且含非平凡状态 → complex；几行协议即可描述 → simple。

| 规则摘要 | 类型 | 影响范围 | 归属 | 状态 | 来源 | 参见 |
|:--|:--|:--|:--|:--|:--|:--|
|  | simple / complex |  | page / shared / global | confirmed / candidate / pending |  | `ux_handoff_global_{topic}.md`（complex 时必填） |

### 2.1 内联展开：轻量全局/跨页规则

> simple 类型规则在此逐条展开，每条包含：规则描述、适用页面、约束条件、来源证据。

<!-- 示例：
#### 规则：Toast 统一规范
- **描述**：操作反馈 toast 统一底部居中，持续 2s
- **适用页面**：全部页面
- **约束**：不阻断操作，不保留输入
- **来源**：交互稿节点 "Global Toast Spec"
-->

## 3. 待确认项汇总

> 汇总所有 per-entity handoff 中的待确认项，便于全局追踪。
>
> 当存在 `ux_confirmation_sheet.xlsx` 时，在此处插入提示：
> `> ⚠️ 当前存在 N 项待外部确认（见 ux_confirmation_sheet.xlsx）。确认单回传后，对 AI 说「回放UX确认单」即可自动更新。

| 编号 | 所属 handoff | 问题摘要 | 确认角色 | 跑偏风险 | 阻塞级别 | 推荐选项 | 可继续假设 | 建议确认时机 | 影响范围 | 状态 |
|:--|:--|:--|:--|:--|:--|:--|:--|:--|:--|:--|
|  | `ux_handoff_{name}.md` |  | product / interaction / visual / technical / host / data / mixed | state / data / navigation / effect / ownership / ui-carrier / acceptance / none | pre-blocking / blocking / non-blocking |  |  | now / before-implementation / before-visual-landing / later |  | open / resolved |

### 3.1 列语义

| 列 | 来源 | 说明 |
|:--|:--|:--|
| **编号** | per-handoff §15 | 唯一标识，格式 `{前缀}-{序号}`（如 H1-001, G1-001） |
| **所属 handoff** | index 汇总时填入 | 对应 handoff 文件名 |
| **问题摘要** | per-handoff §15 | 待确认问题的简洁描述 |
| **确认角色** | per-handoff §15 | 负责回答此问题的角色（product/interaction/visual/technical/host/data/mixed） |
| **跑偏风险** | per-handoff §15 | 若此项未确认，可能导致哪些方面跑偏（state/data/navigation/effect/ownership/ui-carrier/acceptance/none） |
| **阻塞级别** | per-handoff §15 | pre-blocking：不确认无法开始任何相关开发；blocking：不确认相关功能无法交付；non-blocking：可先实现后续修正 |
| **推荐选项** | AI 基于 DSL 上下文推断 | AI 的最佳判断。无明确推断依据时写 `需确认方提供` |
| **可继续假设** | AI 给出的安全 fallback | 若此项未确认，开发可基于什么假设先行推进。若不存在安全假设，写 `不可假设，必须确认` |
| **建议确认时机** | AI 基于阻塞级别和返工成本推断 | now：须立即确认；before-implementation：开发启动前；before-visual-landing：视觉合入前；later：不阻塞当前迭代 |
| **影响范围** | per-handoff §15 | 确认后返工涉及的 handoff section 列表，用于估算成本 |
| **状态** | 随确认进展更新 | open：待确认；resolved：已确认并合入
