---
name: "tac-domain-design"
version: 0.4.5
description: "业务与领域设计独立入口：基于 PRD 派生项目级 baseline 的业务与领域设计文档（限界上下文 / 聚合根 / 领域事件 / 业务规则 / Ubiquitous Language / 各 BC 能力清单 / 场景-行为联动表）。触发：用户提供 PRD/需求文档并要求'做业务领域设计''出 DDD 设计''拆限界上下文''聚合根建模''业务规则梳理'等单阶段任务。若用户同时要 HLD/DLD/准出标准 四阶段全套，请改用编排器 `tac-feature-analysis`。"
---

## 适用范围

本 Skill 是**单阶段独立工具**，只负责"业务与领域设计"一份产物的落盘。它是项目级 baseline 设计文档链的第一阶段，下游是 `tac-hld`（概要设计）。

- 跨项目可移植：不假设特定项目目录约定
- 与 `tac-feature-analysis`（四阶段编排器）共存：本 Skill 输出与四阶段编排器中 Stage 1 产物**路径、frontmatter、模板完全一致**，二者可互相消费
- 不处理单 Feature/单 Bug（交给单 Feature 入口工具）

支持**首次模式**（PRD 0→1 派生）与**维护模式**（PRD 已跑过一次，按变化清单局部修改）。模式判定：Step 0 输入「迭代来源」字段 → 维护模式；为空 → 首次模式。

## 产物

| 项 | 内容 |
|----|------|
| 落盘路径 | `persistent-assets/design/_baseline/00-业务与领域设计.md`（项目级 baseline 固定路径） |
| frontmatter | `stage: 00-business-design` / `scope: <feature-slug 或本次 PRD 主题>` / `version` / `date` / `sources` |
| 模板 | `templates/业务与领域设计.template.md` |
| 派生方法 | `references/derivation-method.md` |

## 硬规则（不可绕过）

1. **纯文档生产**：不修改业务代码、不调用实现类 Skill、不跑构建命令
2. **双闸门**：产物落盘后必须经过自审 5 类 → 用户审两道闸门
3. **Commit 边界**：Skill 不执行 `git add` / `git commit`。落盘后由用户在用户审通过后自行 commit（按所在仓库的提交规范）
4. **维护追溯**：维护模式每次修改必须在产物头部「变更记录」段追加条目，与变化清单 1:1

## Step 0: 收集 PRD 输入（不可跳过）

检查用户输入是否覆盖以下字段。**缺失任何必填项必须追问，不得猜测。**

| 字段 | 必填 | 说明 |
|------|------|------|
| PRD 文件路径 | 是 | 仓库内或绝对路径，必须可读 |
| feature-slug | 是 | 写入 frontmatter `scope` 字段，kebab-case，如 `download-purify` |
| 范围声明 | 是 | in-scope / out-of-scope；维护模式下每个 in-scope 项需标注「沿用 / 修改 / 新增」 |
| 上游约束 | 否 | 已有领域模型、术语表、上下文映射 |
| **迭代来源** | 否 | 上一版 feature-slug + 该版本最末次 commit hash；填写即进入维护模式 |
| **变化清单** | 维护模式必填 | 按类型分组（澄清/修改/新增/废弃/重命名），每条引用 PRD 章节号 |

收齐后判断模式：

- **首次模式**：确认 `persistent-assets/design/_baseline/` 目录存在（由 `tcli init` 创建），通读 PRD 后输出**章节大纲与初步范围识别**给用户确认，确认后进入 Step 1
- **维护模式**：跳到 Step M（本文末），仅修改影响章节 + 头部追加变更记录

## Step 1: 派生业务与领域设计

读 `references/derivation-method.md` 获取详细派生方法、必填章节、自审规则、用户审 prompt。落盘到 `persistent-assets/design/_baseline/00-业务与领域设计.md`（覆盖式写入），跑双闸门。**不要 commit**。

## Step 2: 交棒

产物审批通过后，按需建议下游路径之一（**不得直接调用**）：

- 继续概要设计：建议用户启动 `tac-hld`，以本产物作为上游输入
- 进入单 Feature 规格化：建议用户对每个 BC / 能力单元启动单 Feature 入口工具（如 `tac-feature` 或所在项目等价工具）
- 走四阶段全套：建议用户改用 `tac-feature-analysis`（不重跑本阶段，直接复用本产物进入 Stage 2）

输出末尾给出"建议命令"清单（不执行），用户决定下一步。

## Step M: 维护模式（PRD 变化时使用）

进入条件：Step 0 输入了「迭代来源」字段。

1. 与用户确认变化清单按 5 类分组（澄清 / 修改 / 新增 / 废弃 / 重命名）
2. 输出**单文件影响清单**（每条变化对应本产物哪些章节）给用户审，避免改漏
3. 按清单局部修改 `00-业务与领域设计.md`，头部追加「变更记录」行
4. 跑 5 类自审仅对变化章节判 + 用户审 prompt 突出变化清单
5. 交棒（commit 由用户决定）

> **跨阶段维护影响**：若本次变化影响 HLD/LLD/准出标准，请在 Step 2 交棒时显式提示用户对应启动 `tac-hld` / `tac-lld` / `tac-release-gate-generate` 的维护模式。本 Skill 只负责本阶段；不输出跨阶段影响矩阵（那是 `tac-feature-analysis` 编排器的职责）。

## 双闸门

**自审 5 类（落盘后立刻执行）：**

1. **Placeholder**：是否有 TODO / TBD / 占位符未填
2. **Consistency**：内部章节是否互相矛盾
3. **Scope**：是否聚焦本阶段（业务领域阶段不写 HTTP 路径、不写技术栈、不写 UI 控件）
4. **Ambiguity**：是否有 2 种以上合理解读的句子
5. **Domain Purity**：是否提到了具体技术栈/存储路径/UI 控件？是否用"模块/服务/组件"等技术划分词替代业务概念？限界上下文的语言模型描述是否真的从业务视角写？

发现问题 inline 修复，无需二审。

**用户审 prompt（逐字模板）：**

> 业务与领域设计产物 `persistent-assets/design/_baseline/00-业务与领域设计.md` 已落盘（未 commit，由你审阅后自行决定何时 commit）。
>
> 已通过 5 类自审：Placeholder / Consistency / Scope / Ambiguity / Domain Purity。
>
> 关键决策摘要：
> - 子域分类：核心 = `<...>`，支撑 = `<...>`，通用 = `<...>`
> - 限界上下文：`<逗号分隔列表>`
> - 上下文映射最复杂的一处：`<...>`
>
> 请审阅，确认后由你 commit（按所在仓库的提交规范）。如需修改请直接指出章节/段落，我会改完重审。

## 与项目治理的对接（自适应，跨项目可移植）

本 Skill 不假设特定项目的目录约定与文件名。按以下检测顺序自适应消费项目治理资产；**未命中跳过**，不阻塞流程。

- 项目入口文件：`PROJECT.md` / `AGENTS.md` / `CLAUDE.md` / `GEMINI.md` / `.cursorrules` / `README.md`（按序探测命中即读，用于场景 → 必读文档映射）
- 既有领域模型：`persistent-assets/design/_baseline/00-业务与领域设计.md`（如已存在，维护模式必读）
- Ubiquitous Language 资产：项目入口文件显式声明的术语表位置
- 文档索引：仓库根 `INDEX.md` / `TOC.md` / `README.md` 目录段（产物落盘后向用户提示是否追加索引行）
