---
name: "tac-feature-analysis"
version: 0.4.5
description: "PRD/需求文档分析入口，按四阶段派生项目级 baseline 设计文档：业务与领域设计 → 概要设计 → 详细设计 → 准出标准设计。触发：用户提供 PRD/需求文档并要求'做设计''出 HLD''出 DLD''出概要设计''出详细设计''出验收标准''做整体设计''PRD 转设计''PRD 分析'等。所在环节：① 需求输入（PRD 维度）。"
---

## 适用范围

本 Skill 处理**项目/版本级 PRD**，输出一组互相派生的设计文档；不处理单 Feature/单 Bug（应交给单 Feature/单 Bug 入口工具，本仓库实例：`tac-feature` / `tac-bugfix`）。

**跨项目可移植**：本 Skill 不假设特定项目的目录约定与文件名；所有"必读项目文件"在 reference 中以**自适应检测**的方式描述（详见末尾"与项目治理的对接"章节）。

支持两种工作模式：

- **首次模式（Fresh）**：从 PRD 0 → 1 派生 4 份产物（默认入口）。流程见 Step 0 → Step 5
- **维护模式（Maintenance）**：PRD 已经跑过一次 Skill，后续变化（澄清 / 修改 / 新增 / 废弃 / 重命名）按**影响矩阵 + 局部修改 + 变更记录**演进既有产物。流程见本 SKILL.md 末尾「Step M（维护模式）」+ 详细操作手册 `references/maintenance-mode.md`

模式判定：用户在 Step 0 输入「迭代来源」字段（上一版 feature-slug + commit hash）→ 进入维护模式；为空 → 进入首次模式。

四阶段产物（项目级 baseline，固定落盘路径）：

| 阶段 | 产物 | 落盘路径 | frontmatter `stage` 值 |
|------|------|----------|------------------------|
| Stage 1 | 00-业务与领域设计.md | `persistent-assets/design/_baseline/00-业务与领域设计.md` | `00-business-design` |
| Stage 2 | 01-概要设计.md | `persistent-assets/design/_baseline/01-概要设计.md` | `01-hld-design` |
| Stage 3 | 02-详细设计.md | `persistent-assets/design/_baseline/02-详细设计.md` | `02-dld-design` |
| Stage 4 | 03-准出标准设计.md | `persistent-assets/design/_baseline/03-准出标准设计.md` | `03-acceptance-design` |

> **路径来源**：操作手册 §1.5.2「`persistent-assets/design/_baseline/` 项目级 baseline 命名」。这 4 份产物是**项目级跨 feature 共用**的设计基线，落盘路径与文件名固定，不再随 feature-slug 变化。

`feature-slug` 仍由用户在 Step 0 提供，但仅用于：(1) 写入产物 frontmatter `scope` 字段作为本次 PRD 主题标识；(2) Step 5 交棒时为下游单 Feature 入口工具提供 slug 参考。**不再用于落盘目录命名**。

产物 frontmatter 必须符合操作手册 §1.5.5 统一约定：`stage` / `scope` / `version` / `date` / `sources` 字段齐备。

## 阶段间硬规则（不可绕过）

1. **顺序锁定**：Stage N 必须落盘且**用户审批通过**后，才能进入 Stage N+1。不得合并阶段、不得跳过阶段。
2. **派生约束**：每阶段必须显式声明上游输入文件，并在自审中检查"上游元素是否被完整派生"。详见 `references/cross-stage-consistency.md`。
3. **禁止越界**：本 Skill 是**纯文档生产 Skill**。在 Stage 4 完成前：
   - 不得调用任何实现类 Skill / 工具（如 Speckit 体系的 `speckit-implement`、Feature 入口工具如本仓库的 `tac-feature` 等）
   - 不得修改任何 `app/`、`feature-*/`、`platform-*/` 业务代码
   - 不得运行 `./gradlew assemble*` 等构建命令
4. **双闸门**：每阶段产物落盘后必须经过**自审 → 用户审**两道闸门，自审失败需 inline 修复，用户审拒绝需重写并重审。
5. **Commit 边界**：Skill 不执行 `git add` / `git commit`。每阶段产物**只落盘**，由用户在用户审通过后自行 commit（按所在仓库的 commit message 规范；如仓库有 commit-review 工具按其指引——本仓库实例：`tac-commit-review` 八字段规范）。Skill 可以建议 commit message 草稿，但不得直接调用 git。
6. **变更追溯**：维护模式下每次修改必须在受影响产物头部「变更记录」段追加条目，且每条变更记录的"影响章节"列必须与 M1 影响矩阵 1:1。修改未在变更记录留痕、或留痕未对齐影响矩阵，视为不合规，重审退回。

## Step 0: 收集 PRD 输入（不可跳过）

检查用户输入是否覆盖以下字段。**缺失任何必填项必须追问，不得猜测。**

| 字段 | 必填 | 说明 |
|------|------|------|
| PRD 文件路径 | 是 | 仓库内或绝对路径，必须可读 |
| feature-slug | 是 | 产物目录名，简短英文/拼音 kebab-case，如 `download-purify` |
| 范围声明 | 是 | in-scope（本次必须覆盖）/ out-of-scope（明确不做）；维护模式下每个 in-scope 项需标注「沿用 / 修改 / 新增」之一，废弃项落入 out-of-scope |
| 上游约束 | 否 | 已有文档/接口/技术栈，影响下游派生 |
| 截止时间 | 否 | 影响 Stage 拆分粒度（紧 → 合并某些子模块） |
| **迭代来源** | 否 | 上一版 feature-slug + 该版本最末次 commit hash（例：`appstore-srs-v1.2 @ 45de47d`）；填写则进入维护模式，为空则首次模式 |
| **变化清单** | 维护模式必填 | 按类型分组列出（澄清 / 修改 / 新增 / 废弃 / 重命名），每条引用 PRD 章节号；详见 `references/maintenance-mode.md` M0 |

**追问模板（缺失时）：**

> 为开展 PRD 分析，请补充：
>
> 【PRD 路径】：<文件路径，必须可读>
> 【feature-slug】：<产物目录名，kebab-case，如 download-purify>
> 【范围声明】：in-scope 列项 / out-of-scope 列项
> 【上游约束】：<已有设计/接口/技术栈，可选>
> 【截止时间】：<可选>

收齐后判断模式：

- **首次模式**（无迭代来源）：确认 `persistent-assets/design/_baseline/` 目录存在（由 `tcli init` 创建），通读 PRD 后输出**章节大纲与初步范围识别**给用户确认，确认后进入 Step 1
- **维护模式**（有迭代来源）：跳到 Step M，按 `references/maintenance-mode.md` M0~M5 流程执行，**不**进入 Step 1~4 全集生成

## Step 1: 业务与领域设计

读 `references/stage-1-business-domain.md` 获取详细派生方法、必填章节、自审规则、用户审 prompt。落盘到 `persistent-assets/design/_baseline/00-业务与领域设计.md`（覆盖式写入，frontmatter `stage: 00-business-design`），跑双闸门。**不要 commit**（见硬规则 5）。

## Step 2: 软件概要设计

跑跨阶段一致性检查（`references/cross-stage-consistency.md` 第 2 节），通过后读 `references/stage-2-high-level-design.md`，落盘到 `persistent-assets/design/_baseline/01-概要设计.md`（frontmatter `stage: 01-hld-design`），跑双闸门。**不要 commit**（见硬规则 5）。

## Step 3: 软件详细设计

跑跨阶段一致性检查（`references/cross-stage-consistency.md` 第 3 节），通过后读 `references/stage-3-detailed-design.md`，落盘到 `persistent-assets/design/_baseline/02-详细设计.md`（frontmatter `stage: 02-dld-design`），跑双闸门。**不要 commit**（见硬规则 5）。本阶段产物易遗漏边角，可选派 `general-purpose` 子代理按 `references/dld-reviewer-prompt.md` 做独立深审。

## Step 4: 软件验收标准

跑跨阶段一致性检查（`references/cross-stage-consistency.md` 第 4 节），通过后读 `references/stage-4-acceptance.md`，落盘到 `persistent-assets/design/_baseline/03-准出标准设计.md`（frontmatter `stage: 03-acceptance-design`），跑双闸门。**不要 commit**（见硬规则 5）。可选派 `general-purpose` 子代理按 `references/acceptance-reviewer-prompt.md` 做独立深审。

## Step 5: 交棒

四份文档全部审批通过后，按需建议下游路径之一（**不得直接调用**）：

- 多 Feature 拆解：建议用户对每个 Stage 3 模块通过单 Feature 入口工具启动后续流程（如 Speckit 体系的 `speckit-specify` / 项目自研入口如本仓库 `tac-feature`）
- 单 Feature 直进：建议用户把 Stage 1+2 作为 spec 输入直接进入规格化工具（如 `speckit-specify` 或所在项目的等价工具）

输出末尾给出"建议命令"清单（不执行），用户决定下一步。

## Step M: 维护模式（PRD 变化时使用）

进入条件：Step 0 输入了「迭代来源」字段。详细流程读 `references/maintenance-mode.md` 全文执行 M0~M5：

- **M0**：与用户确认目录策略（沿用旧 slug / 新建复制 / 新建从零派生）；细化变化清单
- **M1**：输出影响矩阵（每条变化对 4 份产物各章节的影响）给用户审，避免改漏
- **M2**：按矩阵局部修改 4 份产物；每份头部追加「变更记录」段（硬规则 6）
- **M3**：跑 `cross-stage-consistency.md` 增量版反查（仅校验影响章节及其依赖）
- **M4**：双闸门（5 类自审仅对变化章节判 + 用户审 prompt 突出变化清单）
- **M5**：交棒（与 Step 5 同；commit 推荐单 commit 含 4 份所有改动）

维护模式下**不**走 Step 1~4 全集生成，但仍受阶段间硬规则 1~6 约束（顺序锁定 / 派生约束 / 禁止越界 / 双闸门 / Commit 边界 / 变更追溯）。

## 双闸门（每阶段共用规则）

**自审（5 类，落盘后立刻执行）：**

1. **Placeholder**：是否有 TODO / TBD / 占位符未填
2. **Consistency**：内部章节是否互相矛盾
3. **Scope**：是否聚焦本阶段（业务领域阶段不写 HTTP 路径、详细设计阶段不空谈业务价值）
4. **Ambiguity**：是否有 2 种以上合理解读的句子
5. **Stage-specific 第 5 类**（详见各阶段 reference）

发现问题 inline 修复，无需二审。

**用户审 prompt（逐字模板）：**

> Stage <N> 产物 `<path>` 已落盘（未 commit，由你审阅后自行决定何时 commit）。
>
> 已通过 5 类自审。请审阅，确认后由你 commit（按所在仓库的提交规范），并告诉我进入 Stage <N+1>。
>
> 如需修改请直接指出（章节/段落/具体语句），我会改完重审。

用户回复"通过/确认/继续"后才能进入下一阶段；commit 与否、何时 commit 完全由用户决定，Skill 不催促也不代办。任何修改诉求都需重落盘+重审。

## 与项目治理的对接（自适应，跨项目可移植）

本 Skill 不假设特定项目的目录约定与文件名。在 Step 1/2/3 派生时按以下检测顺序自适应消费项目治理资产；**未命中跳过**，不阻塞流程。

### 1. 项目入口与场景映射（按需检测）

按以下顺序探测项目入口文件，命中即读：

- `PROJECT.md` / `AGENTS.md` / `CLAUDE.md` / `GEMINI.md` / `.cursorrules` / `README.md`（仓库根）

入口文件中若有"场景 → 必读文档"映射（如"新增模块 / 依赖选型 / 网络通信 / 存储 / 分层调整 → 工程规范"），按本次 PRD 命中的场景读取被映射的规范文件作为 Stage 2/3 的"既有约束"输入。**Skill 不固化场景条目**——避免跨项目漂移。

### 2. 工程规范 / 编码规范 / 流程规范（按需检测）

按以下顺序探测项目规范文档，命中即作为 Stage 2/3 派生的"既有约束"输入；未命中则按通用 Android/Kotlin 最佳实践派生（默认 Jetpack 生态）。

- `.specify/memory/*.md`（Speckit 体系约定，含主宪章与专项宪章）
- `persistent-assets/design/_baseline/01-概要设计.md`（架构约束来源）
- `persistent-assets/governance/**/*.md`（团队治理资产）
- `ENGINEERING.md` / `ARCHITECTURE.md` / `CONTRIBUTING.md`（仓库根标准位）
- 项目入口文件中显式声明的其他位置

### 3. 文档索引追加提示（按需检测）

按以下顺序探测文档索引文件，命中则在 Stage 1 完成后向用户提示追加索引行；未命中跳过：

- 仓库根 `INDEX.md` / `TOC.md` / `README.md` 中的目录段
- 项目入口文件中显式声明的索引位置（本仓库实例：仓库根 `Android-AI编程工程实践指南.md` 附录）

索引行的写入与 commit 由用户自行决定。

### 4. 既有技术栈快照（按需检测）

按以下顺序探测项目当前技术栈快照，避免重复造轮子：

- 项目入口文件中的「Active Technologies」段（CLAUDE.md 风格）
- `gradle/libs.versions.toml` / `package.json` / `Cargo.toml` / `requirements.txt` / `go.mod` 等
- 项目根 `build.gradle*` / `settings.gradle*`

未命中则推断为新项目首次落地，按 PRD NFR + 通用最佳实践派生。

### 5. 与同类工具的边界（概念层）

本 Skill 在工具链中的定位以**功能角色**而非具体工具名描述：

| 角色 | 定义 | 与本 Skill 关系 | 本仓库实例（参考） |
|------|------|---------------|-------------------|
| **项目级专项规范工具** | 一次性配置，约束所有需求分析过程 | 互补——专项规范定义"应该怎么分析"，本 Skill 是"按规范产出 4 份具体设计" | `tac-feature-analysis` |
| **单 Feature 规格化工具** | 对单一 Feature 生成 spec.md | 下游消费方——本 Skill 输出 4 份产物可作为多个该类工具的上游输入 | `speckit-specify` / `tac-feature` |
| **实现入口工具** | 把 spec / plan / tasks 转为代码实现 | 不直接对接——本 Skill 是纯文档生产，不进入实现阶段；交棒由用户决定 | `speckit-implement` / `tac-feature` 后续流程 |
| **Commit 评审工具** | 校验 commit message 规范 | 协作——Skill 在用户审 prompt 中引用所在仓库的提交规范作为提示 | `tac-commit-review` 八字段 |

**具体工具名称按各项目落地约定**——本 Skill 不强制依赖特定工具链；上表"本仓库实例"列仅作参考，跨项目使用时按所在仓库等价工具替换。

### 6. 跨项目使用 checklist

首次在新项目跑本 Skill 前，建议确认：

- [ ] 项目入口文件已识别（如有）；未命中可用 `README.md` 作为兜底
- [ ] 项目工程规范位置已识别（如有）；未命中按通用 Android/Kotlin 最佳实践
- [ ] 项目 commit message 规范已识别（如有）；未命中按 Conventional Commits 或项目自定义
- [ ] 项目级 baseline 目录 `persistent-assets/design/_baseline/` 已存在（由 `tcli init` 创建；若是手工搭建项目，需先 `mkdir -p` 该目录）
