---
name: "tac-lld"
version: 0.4.5
description: "软件详细设计独立入口：基于概要设计 baseline 派生详细设计文档（模块详述 / 对外接口契约 / 状态机 / 时序图 / 数据模型 / 并发与一致性 / 可观测性埋点）。触发：用户提供已落盘的概要设计 baseline 并要求'出详细设计''出 LLD''做接口契约''画状态机''出时序图''出数据模型'等单阶段任务。若用户同时要业务领域/HLD/准出标准 四阶段全套，请改用编排器 `tac-feature-analysis`。"
---

## 适用范围

本 Skill 是**单阶段独立工具**，只负责"软件详细设计"一份产物的落盘。上游是 `tac-hld`（概要设计），下游是 `tac-release-gate-generate`（准出标准生成）或单 Feature 入口工具。

- 跨项目可移植：不假设特定项目目录约定
- 与 `tac-feature-analysis`（四阶段编排器）共存：本 Skill 输出与四阶段编排器中 Stage 3 产物**路径、frontmatter、模板完全一致**，二者可互相消费
- 不处理单 Feature/单 Bug
- 本阶段产物易遗漏边角，可选派 `general-purpose` 子代理按 `references/lld-reviewer-prompt.md` 做独立深审

**术语说明**：LLD = Low-Level Design（详细设计）。本项目使用 LLD 指代国内通常说的"详细设计"，与 HLD（概要设计）相对。

支持**首次模式**与**维护模式**。

## 产物

| 项 | 内容 |
|----|------|
| 落盘路径 | `persistent-assets/design/_baseline/02-详细设计.md`（项目级 baseline 固定路径） |
| frontmatter | `stage: 02-dld-design` / `scope: <feature-slug 或本次 PRD 主题>` / `version` / `date` / `sources` |
| 模板 | `templates/软件详细设计.template.md` |
| 派生方法 | `references/derivation-method.md` |
| 上游一致性检查 | `references/consistency-with-hld.md` |
| 独立深审 prompt | `references/lld-reviewer-prompt.md` |

> **frontmatter `stage` 字段历史兼容**：值仍为 `02-dld-design`（与 `tac-feature-analysis` 编排器现有产物一致），不引入 `02-lld-design` 别名，避免双 surface 漂移。

## 硬规则（不可绕过）

1. **前置依赖**：必须存在已落盘且经用户审批的 `01-概要设计.md`（首次模式）或上一版 `02-详细设计.md`（维护模式）
2. **纯文档生产**：不修改业务代码、不调用实现类 Skill、不跑构建命令
3. **双闸门**：产物落盘后必须经过自审 5 类 → 用户审两道闸门
4. **Commit 边界**：Skill 不执行 git；落盘后由用户自行 commit
5. **维护追溯**：维护模式每次修改必须在产物头部「变更记录」段追加条目

## Step 0: 收集输入（不可跳过）

| 字段 | 必填 | 说明 |
|------|------|------|
| 概要设计路径 | 是 | 默认 `persistent-assets/design/_baseline/01-概要设计.md`；不存在则拒绝执行 |
| 业务与领域设计路径 | 是 | 默认 `persistent-assets/design/_baseline/00-业务与领域设计.md`；用于业务规则/聚合根/术语回查 |
| feature-slug | 是 | 写入 frontmatter `scope` 字段 |
| 模块裁剪 | 否 | 若只想对某些模块出 LLD（如增量场景），列出模块名 |
| **迭代来源** | 否 | 上一版 commit hash；填写即进入维护模式 |
| **变化清单** | 维护模式必填 | 按类型分组 |

收齐后跑 `references/consistency-with-hld.md` §1（HLD 完整性反查），通过后进入 Step 1。

## Step 1: 派生详细设计

读 `references/derivation-method.md` 获取派生方法、必填章节、自审规则。落盘到 `persistent-assets/design/_baseline/02-详细设计.md`（覆盖式写入），跑双闸门。**不要 commit**。

**模块数较多（≥6）时可拆分：**
- `02-详细设计.md`（总览 + 索引）
- `02-详细设计-<模块名>.md`（每模块一份，frontmatter `scope` 填模块名）
- 拆分前先与用户确认

## Step 2: 交棒

产物审批通过后，按需建议下游路径之一（**不得直接调用**）：

- 出准出标准：建议用户启动 `tac-release-gate-generate`，以本产物作为上游输入
- 进入单 Feature 实现：建议用户对每个模块启动单 Feature 入口工具（如 `tac-feature` 或所在项目等价工具），LLD 作为 plan/tasks 派生的上游
- 走四阶段全套：建议用户改用 `tac-feature-analysis`

## Step M: 维护模式

进入条件：Step 0 输入了「迭代来源」字段。

1. 与用户确认变化清单按 5 类分组
2. 输出**单文件影响清单**（每条变化对应本产物哪些模块/章节）给用户审
3. 按清单局部修改 `02-详细设计.md`（或拆分子文件），头部追加「变更记录」行
4. 跑 5 类自审仅对变化章节判 + 用户审 prompt 突出变化清单
5. 交棒

> **跨阶段维护影响**：若本次变化影响业务领域/HLD/准出标准，请在 Step 2 显式提示用户对应启动 `tac-domain-design` / `tac-hld` / `tac-release-gate-generate` 的维护模式。本 Skill 只负责本阶段。

## 双闸门

**自审 5 类：**

1. **Placeholder**：是否有 TODO / TBD / 占位符未填
2. **Consistency**：内部章节是否互相矛盾
3. **Scope**：是否聚焦本阶段（LLD 阶段不空谈业务价值、不写架构选型理由）
4. **Ambiguity**：是否有 2 种以上合理解读的句子
5. **Contract Completeness**：每个对外接口必须同时给出六要素（接口类型 / 签名 / 前置 / 后置 / 错误码 / 幂等），缺一不可；状态机非法转移是否显式拒绝；时序图是否覆盖了接口契约里全部错误码的触发路径；数据模型字段是否对应到聚合根中的实体/值对象。详见 `references/derivation-method.md` §6

**可选独立深审**：模块数 ≥ 5 或用户主动要求时，派 `general-purpose` 子代理按 `references/lld-reviewer-prompt.md` 执行二次复核。

**用户审 prompt（逐字模板）：**

> 详细设计产物 `persistent-assets/design/_baseline/02-详细设计.md` 已落盘（未 commit，由你审阅后自行决定何时 commit）。
>
> 已通过 5 类自审：Placeholder / Consistency / Scope / Ambiguity / Contract Completeness。
>
> 关键决策摘要：
> - 模块数：`<N>`，详述模块：`<逗号分隔列表>`
> - 接口契约总数：`<M>`
> - 状态机数：`<K>`
> - 最复杂时序图：`<...>`
> - 关键并发/一致性决策：`<...>`
>
> （可选）如需独立深审，可派 general-purpose 子代理按 `references/lld-reviewer-prompt.md` 执行。
>
> 请审阅，确认后由你 commit。如需修改请直接指出模块/章节/段落，我会改完重审。

## 与项目治理的对接（自适应）

按以下检测顺序自适应消费项目治理资产；未命中跳过：

- 项目入口文件：`PROJECT.md` / `AGENTS.md` / `CLAUDE.md` / `GEMINI.md` / `README.md`
- 编码与工程规范：`.specify/memory/*.md` / `persistent-assets/governance/**/*.md` / `CONTRIBUTING.md` / `ENGINEERING.md` / `ARCHITECTURE.md`
- 命名约定与错误码体系：项目入口文件显式声明的位置；未命中按通用 Android/Kotlin 风格（驼峰命名、kebab-case 资源、错误码 `E_<MODULE>_<KIND>_<SEQ>` 形式）
- 既有同类模块代码：按需查阅，参考接口风格与命名
