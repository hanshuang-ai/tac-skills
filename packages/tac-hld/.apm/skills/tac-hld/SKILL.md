---
name: "tac-hld"
version: 0.4.5
description: "软件概要设计独立入口：基于业务与领域设计 baseline 派生概要设计文档（技术栈选型 / 架构风格 / 模块清单 / 模块间依赖 / 外部依赖 / 跨切面策略 / NFR 达成路径）。触发：用户提供已落盘的业务与领域设计 baseline 并要求'出概要设计''出 HLD''做架构设计''拆模块''选技术栈'等单阶段任务。若用户同时要业务领域/DLD/准出标准 四阶段全套，请改用编排器 `tac-feature-analysis`。"
---

## 适用范围

本 Skill 是**单阶段独立工具**，只负责"软件概要设计"一份产物的落盘。上游是 `tac-domain-design`（业务与领域设计），下游是 `tac-lld`（详细设计）。

- 跨项目可移植：不假设特定项目目录约定
- 与 `tac-feature-analysis`（四阶段编排器）共存：本 Skill 输出与四阶段编排器中 Stage 2 产物**路径、frontmatter、模板完全一致**，二者可互相消费
- 不处理单 Feature/单 Bug

支持**首次模式**与**维护模式**。模式判定：Step 0 输入「迭代来源」字段 → 维护模式；为空 → 首次模式。

## 产物

| 项 | 内容 |
|----|------|
| 落盘路径 | `persistent-assets/design/_baseline/01-概要设计.md`（项目级 baseline 固定路径） |
| frontmatter | `stage: 01-hld-design` / `scope: <feature-slug 或本次 PRD 主题>` / `version` / `date` / `sources` |
| 模板 | `templates/软件概要设计.template.md` |
| 派生方法 | `references/derivation-method.md` |
| 上游一致性检查 | `references/consistency-with-domain-design.md` |

## 硬规则（不可绕过）

1. **前置依赖**：必须存在已落盘且经用户审批的 `00-业务与领域设计.md`（首次模式）或上一版 `01-概要设计.md`（维护模式）
2. **纯文档生产**：不修改业务代码、不调用实现类 Skill、不跑构建命令
3. **双闸门**：产物落盘后必须经过自审 5 类 → 用户审两道闸门
4. **Commit 边界**：Skill 不执行 git；落盘后由用户在用户审通过后自行 commit
5. **维护追溯**：维护模式每次修改必须在产物头部「变更记录」段追加条目

## Step 0: 收集输入（不可跳过）

检查用户输入是否覆盖以下字段：

| 字段 | 必填 | 说明 |
|------|------|------|
| 业务与领域设计路径 | 是 | 默认 `persistent-assets/design/_baseline/00-业务与领域设计.md`；不存在则拒绝执行 |
| PRD 文件路径 | 是 | 用于 NFR、性能/容量约束追溯 |
| feature-slug | 是 | 写入 frontmatter `scope` 字段 |
| 上游约束 | 否 | 已有架构文档、技术栈快照 |
| **迭代来源** | 否 | 上一版 commit hash；填写即进入维护模式 |
| **变化清单** | 维护模式必填 | 按类型分组（澄清/修改/新增/废弃/重命名） |

收齐后检查前置：

- 首次模式：跑 `references/consistency-with-domain-design.md` §1（Stage 1 完整性反查），通过后进入 Step 1
- 维护模式：跳到 Step M

## Step 1: 派生概要设计

读 `references/derivation-method.md` 获取派生方法、必填章节、自审规则、用户审 prompt。落盘到 `persistent-assets/design/_baseline/01-概要设计.md`（覆盖式写入），跑双闸门。**不要 commit**。

## Step 2: 交棒

产物审批通过后，按需建议下游路径之一（**不得直接调用**）：

- 继续详细设计：建议用户启动 `tac-lld`，以本产物作为上游输入
- 进入单 Feature 实现：建议用户对每个模块启动单 Feature 入口工具（如 `tac-feature` 或所在项目等价工具）
- 走四阶段全套：建议用户改用 `tac-feature-analysis`

## Step M: 维护模式

进入条件：Step 0 输入了「迭代来源」字段。

1. 与用户确认变化清单按 5 类分组
2. 输出**单文件影响清单**（每条变化对应本产物哪些章节）给用户审
3. 按清单局部修改 `01-概要设计.md`，头部追加「变更记录」行
4. 跑 5 类自审仅对变化章节判 + 用户审 prompt 突出变化清单
5. 交棒

> **跨阶段维护影响**：若本次变化影响业务领域上游/LLD/准出标准，请在 Step 2 显式提示用户对应启动 `tac-domain-design` / `tac-lld` / `tac-release-gate-generate` 的维护模式。本 Skill 只负责本阶段。

## 双闸门

**自审 5 类：**

1. **Placeholder**：是否有 TODO / TBD / 占位符未填
2. **Consistency**：内部章节是否互相矛盾
3. **Scope**：是否聚焦本阶段（HLD 阶段不写函数签名、不画类图、不写完整 SQL）
4. **Ambiguity**：是否有 2 种以上合理解读的句子
5. **Module Cohesion**：每个模块是否对应**不超过 1 个**限界上下文？跨上下文 = 拆分。模块清单中是否存在职责描述含"和/以及/还包括"等连接词把多种事拼凑？模块间通信是否被错误地解为"共享数据库表"？外部依赖的降级策略是否真的可执行？NFR 达成路径的"如何度量"是否给出可观测信号？

**用户审 prompt（逐字模板）：**

> 概要设计产物 `persistent-assets/design/_baseline/01-概要设计.md` 已落盘（未 commit，由你审阅后自行决定何时 commit）。
>
> 已通过 5 类自审：Placeholder / Consistency / Scope / Ambiguity / Module Cohesion。
>
> 关键决策摘要：
> - 技术栈推荐：`<...>`，关键理由 `<...>`
> - 架构风格：`<...>`，主要反驳替代：`<...>`
> - 模块数：`<N>`，最复杂依赖关系：`<...>`
> - 主要外部依赖：`<...>`
> - 风险 Top 3：`<...>`
>
> 请审阅，确认后由你 commit。如需修改请直接指出章节/段落，我会改完重审。

## 与项目治理的对接（自适应）

按以下检测顺序自适应消费项目治理资产；未命中跳过：

- 项目入口文件：`PROJECT.md` / `AGENTS.md` / `CLAUDE.md` / `GEMINI.md` / `README.md`（场景 → 必读文档映射）
- 工程规范：`.specify/memory/*.md` / `persistent-assets/governance/**/*.md` / `ENGINEERING.md` / `ARCHITECTURE.md` / `CONTRIBUTING.md`
- 既有技术栈快照：入口文件 Active Technologies 段 / `gradle/libs.versions.toml` / `package.json` / `Cargo.toml` 等

未命中则按通用 Android/Kotlin 最佳实践派生（默认 Jetpack 生态），并在产物中显式声明。
