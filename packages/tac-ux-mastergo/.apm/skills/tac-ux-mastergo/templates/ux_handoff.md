<!--
  使用说明：
  - 页面/流程 Handoff：全部 16 节均适用，正常填写。
  - 全局规则 Handoff（ux_handoff_global_{topic}.md）：
    以下节的标题和行为与页面 Handoff 不同，其余节保持一致：

    | 节 | 页面 Handoff | 全局规则 Handoff |
    |:--|:--|:--|
    | §2 | 页面语义卡 | **规则协议语义**（协议目的、参与者、作用域、正确/禁止数据来源、页面级细节归属） |
    | §3 | 交互对象清单 | **可填**：若全局规则持有独立交互对象（如边界态提示），列出并标 `—` ID；若无可跳过 |
    | §5 | 状态模型 | **可选**：有状态机则填，无则跳过 |
    | §11 | 全局/跨页规则 | **消费页面证据矩阵**：逐条列出 DSL 中可见的消费页面+节点引用，用表格或叙述说明各页面消费方式 |
    | §12 | 与视觉稿协作说明 | **可选简化**：全局规则不涉及页面视觉映射，可仅列通用视觉组件要求（列比页面版少）；或跳过 |

  - 源链接不在本文件记录，统一登记于 ux_handoff_index.md（本文件写「链接见 index」）。
-->
# <页面或流程名称> UX 交互落地文档

> **生成工具**：tac-ux-mastergo v{从 SKILL.md frontmatter version 字段读取}

## 0. 变更记录

<!--
  Reason 字段决策树（详见 mode_c_maintenance_workflow.md §1）：
  - initial：首次从零生成 handoff，无旧版可对比。
  - interaction-design-update：交互稿/需求/视觉/确认输入发生了真实变化。
  - skill-structural-upgrade：输入未变，技能模板/校验器/质量标准升级（如新增节、归一化列、拆分为多文件）。
  - skill-analysis-enrichment：输入未变，升级后的技能能从既有证据中提取更多精确约束/状态/过渡/待确认项。
  - mixed：上述多种原因同时适用。
  选择 initial 时，§0.2/§0.3 留空；选择后四种时，至少填写 §0.2 或 §0.3。
-->

| Version/Date | Reason | Business rules changed | Summary | Source |
|:--|:--|:--|:--|:--|
|  | initial/interaction-design-update/skill-structural-upgrade/skill-analysis-enrichment/mixed | yes/no |  |  |

## 0.1 影响矩阵

| Area | Changed? | Description | Follow-up |
|:--|:--|:--|:--|
| Page semantics | yes/no |  |  |
| Business rules | yes/no |  |  |
| State model | yes/no |  |  |
| Events/effects | yes/no |  |  |
| Boundary states | yes/no |  |  |
| Data rules | yes/no |  |  |
| Navigation | yes/no |  |  |
| UI coordination | yes/no |  |  |
| Code conflict report | yes/no |  |  |
| Acceptance checklist | yes/no |  |  |

## 0.2 交互更新记录

| Change ID | Type | Source | Previous conclusion | New conclusion | Affected sections | Status |
|:--|:--|:--|:--|:--|:--|:--|
|  | added/modified/deprecated/clarified/conflict-fix |  |  |  |  | confirmed/pending |

## 0.3 分析增强记录

| Enrichment | Type | Previous gap | Input evidence | Conclusion level | Needs confirmation |
|:--|:--|:--|:--|:--|:--|
|  | constraint/boundary-state/state-transition/acceptance/pending-question/global-rule |  |  | explicit/derived/pending/rejected | yes/no |

## 1. 输入与依据

| 来源类型 | 输入物 | 位置/节点/章节 | 用途 | 可信度 |
|:--|:--|:--|:--|:--|
| business-source |  |  |  | confirmed/pending |
| interaction-source |  |  |  | confirmed/pending |
| visual-source |  |  |  | confirmed/pending |
| architecture-source |  |  |  | confirmed/pending |
| code-reference |  | 仅用于冲突检查/复用盘点，不作为业务事实 |  | confirmed/pending |

## 1.1 产物定位与落盘

| 字段 | 说明 |
|:--|:--|
| 当前产物类型 | UX handoff / maintenance update |
| 推荐落盘位置 | 优先使用项目受控的设计/规格文档目录 |
| 是否项目共享真相源 | yes/no |
| 是否仍为临时本地草稿 | yes/no |
| 后续预期消费者 | 开发实现 / UI handoff / 评审 / 维护迭代 |

## 2. 页面语义卡

| 字段 | 结论 | 来源 | 待确认 |
|:--|:--|:--|:--|
| 页面/流程语义 |  |  |  |
| 业务模块 |  |  |  |
| 用户/角色 |  |  |  |
| 入口 |  |  |  |
| 出口 |  |  |  |
| 正确数据来源 |  |  |  |
| 禁止误用的数据来源 |  |  |  |
| 页面自有职责 |  |  |  |
| 共享/外部职责 |  |  |  |
| 页面级细节归属 |  |  |  |

## 2.1 下游稳定契约

| 契约对象 | 稳定名称 | 说明 | 变更规则 |
|:--|:--|:--|:--|
| page semantic name |  |  | 仅在证据变化或用户确认时修改 |
| state names |  |  | 仅在证据变化或用户确认时修改 |
| event names |  |  | 仅在证据变化或用户确认时修改 |
| effect names |  |  | 仅在证据变化或用户确认时修改 |
| shared/global rule names |  |  | 仅在证据变化或用户确认时修改 |

## 3. 交互对象清单

| 交互对象 ID | 对象名称 | 角色 | 来源节点/注释 | 关联状态 | 关联事件 |
|:--|:--|:--|:--|:--|:--|
|  |  |  |  |  |  |

## 4. 业务规则清单

| 规则 ID | 规则描述 | 证据层 | 归属 | 来源类型 | 来源位置 | 示例值是否参与规则 | 置信度 | 待确认 |
|:--|:--|:--|:--|:--|:--|:--|:--|:--|
|  |  | interaction-fact/visual-evidence/implementation-suggestion | page-local/cross-page-shared/host-owned/global/ownership-conflict |  |  | yes/no | confirmed/pending/candidate/assumption |  |

规则描述建议优先使用 `trigger-condition-result` 形式；若无法完整表达，需在相邻章节补足前提或结果。

## 5. 状态模型

| 状态名 | 含义 | 必要数据 | 展示义务 | 可触发事件 | 来源 |
|:--|:--|:--|:--|:--|:--|
|  |  |  |  |  |  |

## 6. 事件/意图/副作用模型

### 6.1 事件/意图

| 事件/意图 | 触发源 | 前置条件 | 参数 | 来源 |
|:--|:--|:--|:--|:--|
|  |  |  |  |  |

### 6.2 副作用

| 副作用 | 类型 | 触发条件 | 结果 | 来源 |
|:--|:--|:--|:--|:--|
|  | navigation/toast/dialog/request/persistence/host/analytics |  |  |  |

### 6.3 反馈文案清单

| 文案 | 反馈类型 | 触发事件 | Guard 条件 | 是否阻断副作用 | 输入是否保留 | 来源 |
|:--|:--|:--|:--|:--|:--|:--|
|  | toast/prompt/error/success/empty/disabled |  |  | yes/no | yes/no/not-applicable |  |

## 7. 状态转移表

| 当前状态 | 事件/意图 | Guard 条件 | 下一状态 | 副作用 | 来源规则 |
|:--|:--|:--|:--|:--|:--|
|  |  |  |  |  |  |

## 8. 边界态矩阵

| 场景 | 进入条件 | 页面表现 | 可操作项 | 恢复/退出规则 | 来源 |
|:--|:--|:--|:--|:--|:--|
| loading |  |  |  |  |  |
| empty |  |  |  |  |  |
| error |  |  |  |  |  |
| offline |  |  |  |  |  |
| disabled |  |  |  |  |  |
| permission-denied |  |  |  |  |  |
| retry |  |  |  |  |  |

## 9. 导航与宿主协作

| 触发 | 目标 | 传参 | 返回/回退规则 | 宿主职责 | 来源 |
|:--|:--|:--|:--|:--|:--|
|  |  |  |  |  |  |

## 10. 数据规则与接口期望

| 数据项/接口 | 来源 | 读写方向 | 转换/过滤/排序规则 | 异常处理 | 待确认 |
|:--|:--|:--|:--|:--|:--|
|  |  | read/write |  |  |  |

说明：此处只描述交互所需的数据语义与接口期望，不展开传输协议、数据访问结构或具体技术实现。

## 11. 全局/跨页规则

<!--
  页面 Handoff：标准表格。
  全局规则 Handoff：标题为「消费页面证据矩阵」，可使用叙述文本逐页列出 DSL 节点证据，也可使用以下简化表格。
-->

### 页面 Handoff 模板

| 规则 | 影响范围 | 当前页消费方式 | 归属建议 | 状态 | 来源 |
|:--|:--|:--|:--|:--|:--|
|  |  |  | page/shared/global | confirmed/candidate/pending |  |

### 全局 Handoff 模板（消费页面证据矩阵）

| 消费页面 | DSL 节点证据 | 消费方式 | 归属 | 来源 |
|:--|:--|:--|:--|:--|
|  |  |  | shared/global |  |

## 12. 与视觉稿协作说明

<!--
  页面 Handoff：完整 11 列表格。
  全局规则 Handoff：可简化为通用视觉组件要求（5~7 列），不含具体页面/区域、视觉节点列。
-->

### 页面 Handoff 模板

| 交互对象 ID | UI 角色 | 映射关系 | 承载级别 | 所属页面/区域 | 视觉节点/组件 | 依赖状态 | 是否关键 | 缺失时的临时承接策略 | 视觉稿缺口 | 备注 |
|:--|:--|:--|:--|:--|:--|:--|:--|:--|:--|:--|
|  |  | primary-carrier/secondary-carrier/state-container/event-trigger/feedback-surface | page/section/component/overlay |  |  |  | required/provisional/optional |  |  |  |

### 全局 Handoff 模板（简化）

| 交互对象 ID | UI 角色 | 映射关系 | 承载级别 | 是否关键 | 备注 |
|:--|:--|:--|:--|:--|:--|
|  |  | primary-carrier/secondary-carrier/state-container/event-trigger/feedback-surface | page/section/component/overlay | required/provisional/optional |  |

无视觉稿时，说明临时骨架策略：

| 临时区域/对象 | 交互职责 | 可替换条件 | UI 稿到达后复查项 |
|:--|:--|:--|:--|
|  |  |  |  |

若视觉稿后补并通过 Mode C 更新，需显式说明：

- 本次仅精化 UI 映射 / 本次同时修正交互事实
- 哪些映射仍为临时承接
- 哪些关键承载位已由正式视觉节点替换

## 13. 实现落点建议

| 责任 | 建议文件/模块 | 类型 | 说明 | 依赖 |
|:--|:--|:--|:--|:--|
| state model |  | docs-only/skeleton/code-follow-up |  |  |
| event/effect |  | docs-only/skeleton/code-follow-up |  |  |
| data rule |  | docs-only/skeleton/code-follow-up |  |  |
| navigation |  | docs-only/skeleton/code-follow-up |  |  |

## 14. 代码冲突检查

| Handoff 规则 | 当前代码状态 | 分类 | 影响 | 建议动作 |
|:--|:--|:--|:--|:--|
|  |  | implemented/missing/wrong/conflicting/reusable/pending |  |  |

## 15. 待确认项

| 编号 | 问题 | 确认角色 | 跑偏风险 | 阻塞级别 | 推荐选项 | 可继续假设 | 建议确认时机 | 影响范围 |
|:--|:--|:--|:--|:--|:--|:--|:--|:--|
|  |  | product/interaction/visual/technical/host/data/mixed | state/data/navigation/effect/ownership/ui-carrier/acceptance/none | pre-blocking/blocking/non-blocking |  |  | now/before-implementation/before-visual-landing/later |  |

待确认项状态使用约定：

- `pre-blocking`：当前阶段若继续会导致分析对象或真相源失真，应立即暂停
- `pending`：证据不足，不能升格为已确认规则
- `blocking`：可先完成当前阶段可靠分析，但进入下一步前必须确认
- `assumption`：仅为继续分析而采用的临时非阻塞假设
- `candidate`：可能成立，但仍需确认的归属或解释
- `non-blocking`：允许继续，但必须显式带标记进入后续产物

待确认项输出原则：

- Handoff 可以完整列出所有仍需追踪的未确认项，不要求只保留影响代码落地的项。
- `跑偏风险` 用于标识该问题是否会影响后续实现选择；不会导致实现跑偏但仍需追踪的项可填 `none`。
- 文案、局部展示、临时命名、视觉微调等不会改变实现方向的缺口，可以保留在 handoff 待确认项中，但不需要进入前置高风险摘要。
- 合并同根问题，优先输出能一次解除多个歧义的确认项。

## 16. 验收清单

- [ ] 每条业务规则都有输入来源。
- [ ] 示例值与真实约束值已区分，未把展示性示例误写成业务规则。
- [ ] 页面语义、正确数据源、禁止误用数据源已明确。
- [ ] 状态模型、事件/意图、副作用、状态转移表已完整。
- [ ] 可见 toast、提示气泡、错误/成功/空态/禁用文案已逐条抽取，并绑定触发事件、Guard 条件和副作用。
- [ ] loading、empty、error、offline、disabled、permission-denied、retry 已覆盖或明确不适用。
- [ ] 跨页/全局规则已拆出或标为候选。
- [ ] 若当前产物是全局/共享规则，已检查相关页面级 owner handoff，未迁入入口 UI、空态文案、列表布局、本地过滤、局部管理控件或页面私有视觉行为。
- [ ] 规则归属冲突已显式标记，没有被强行归类。
- [ ] 与视觉稿的交互对象协作关系已明确；无视觉稿时已标记临时骨架。
- [ ] 下游稳定契约已给出，且稳定名称未被无依据改写。
- [ ] 代码冲突检查未把现有代码当作业务事实。
- [ ] 可能导致代码落地跑偏的待确认项已列出确认角色、跑偏风险、建议确认时机和可继续假设。
