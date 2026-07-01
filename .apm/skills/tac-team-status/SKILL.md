---
name: "tac-team-status"
version: 0.4.5
description: "记录/查询/清理跨工具可见的团队级项目临时状态（模块阶段、接口迁移、发布节奏）。**仅记录满足 4 项硬条件的事实**：跨多人 + 持续 >1 天 + 可过期（≤30 天）+ 现有载体未覆盖。**仅 4 个分类**：模块阶段/接口迁移/发布节奏/其他。**禁止内容**：个人偏好、长期规则、已发生踩坑、单 Feature 进度、可代码/git 查、凭证敏感信息。触发：用户说'标记 X 状态''记一下当前 X''登记冻结期''查看团队状态''清理过期状态'等。所在环节：跨环节，任何阶段都可触发。"
user-invocable: true
---

## 适用边界（先读再用）

| 在 scope | 不在 scope（去对应载体） |
|---------|----------------------|
| 跨多人需要知道的临时事实 | 个人偏好/焦点 → 工具私有 Memory |
| 持续 >1 天、≤30 天的状态 | 长期规则 → `.specify/memory/*-constitution.md`（宪章/专项规范） |
| 模块阶段 / 接口迁移 / 发布节奏 | 已发生的踩坑/根因 → `persistent-assets/governance/issues_and_learnings.md` |
| 现有载体未覆盖的事实 | 单 Feature 内部进度 → `specs/<feature>/` 产物 |
| | 代码/git log 可查的事实 → 不写 |
| | 凭证/密钥/敏感信息 → 安全红线，禁止 |

载体文件：`persistent-assets/governance/team-status.md`（单一真理源，进 git，所有 AI 工具通过 `PROJECT.md` 引用自动读到）。

## Step 0: 路由

按用户意图分流：

| 用户表达 | 走向 |
|--------|------|
| "标记/记录/登记 X 状态" | Step 1-5（写入流） |
| "X 模块当前是 / 处于 / 在 ..." | Step 1-5（写入流） |
| "查看团队状态" / "当前有哪些状态" | Step Q（查询） |
| "清理过期" / "过期检查" | Step E（清理） |

## Step 1: 准入校验（4 项硬条件 AND）

逐项核对，任一缺项立即拒收并提示正确载体：

```
收到写入请求
    │
    ├─ ❓ 含凭证/密钥/敏感信息？
    │     ├── 是 → 立即拒收 + 安全提示，不写 git
    │     └── 否 ↓
    │
    ├─ ❓ 跨多人需要知道？（团队 ≥2 人）
    │     ├── 否 → 引导到工具私有 Memory（Claude/Codex 原生）
    │     └── 是 ↓
    │
    ├─ ❓ 持续 >1 工作日？
    │     ├── 否 → 引导到 IM / 会议纪要
    │     └── 是 ↓
    │
    ├─ ❓ 能给出明确失效日期（≤30 天）？
    │     ├── 否（永久规则） → 引导到宪章/专项规范升级
    │     ├── 否（用户没说） → 反问用户补全失效日
    │     └── 是 ↓
    │
    └─ ❓ 现有载体（宪章/spec/Issues/代码/git log）已覆盖？
          ├── 是 → 引导到对应载体，不重复写
          └── 否 ↓ 进入 Step 2
```

## Step 2: 查重与分类

### 查重

读取 `persistent-assets/governance/team-status.md`，按关键词搜索现有条目：

- **命中相同主题** → 应该是 **更新**（删旧 + 加新），而非追加
- **未命中** → 进入新条目流程

### 分类（强制收口到 4 类）

| 分类 | 适用场景 | 例 |
|------|---------|-----|
| 模块阶段 | 某模块处于某重构/重写/暂停阶段 | "020 进度流重构中，禁直接订阅旧 Flow" |
| 接口迁移 | API/数据源/Schema 切换中 | "021 切换中，platform-api 由 mock→云端" |
| 发布节奏 | release 冻结/解冻/分支节奏 | "release 5/20 冻结期" |
| 其他 | 前三类都不属于 | **必须在条目末尾标注 `（不属前三类原因：xxx）`** |

> 第 4 类是兜底但非自由——必须证明为何不归入前三类，防止变杂物筐。

## Step 3: 补齐三个必填字段

| 字段 | 取值方式 |
|------|---------|
| 失效日期 | 用户明示；未提供则反问；最长不超过 30 天（超过 → 升宪章） |
| 提交人 | 自动取 `git config user.name` |
| 创建日 | 自动取 `date +%Y-%m-%d` |

格式：`[失效 YYYY-MM-DD｜<提交人>｜<创建日>] <一句话内容，≤80 字>`

## Step 4: 量化上限校验

写入前检查：

| 维度 | 上限 | 超限处理 |
|------|------|---------|
| 单条字数 | ≤80 字 | 拆分或精简 |
| 单分类条目数 | ≤10 条 | 触发 review，先调 Step E 清理过期，再考虑是否应升宪章 |
| 文件总条目 | ≤30 条 | 强制 Step E 清理 |
| 同一作者待过期条目 | ≤5 条 | 提示作者先清理 |

## Step 5: 写入与提示提交

1. 按分类追加（或更新）条目到 `persistent-assets/governance/team-status.md`
2. 不自动 `git add` / `git commit`，只打印模板供用户执行：

```bash
git add persistent-assets/governance/team-status.md
# 然后走 /tac-commit-review 完成八字段提交
```

3. 提示团队成员（如有 IM 集成 → 同步到群，否则人工）

## Step Q: 查询当前状态

```bash
cat persistent-assets/governance/team-status.md
# 或仅看条目（跳过用法约定）：
awk '/^## (模块阶段|接口迁移|发布节奏|其他)$/,/^---$/' persistent-assets/governance/team-status.md
```

呈现时按分类列出**未过期**条目，标红 7 天内即将过期的（需配合 expiry 脚本）。

## Step E: 清理过期

```bash
# 路径相对于本 SKILL.md 所在目录（部署后位于 .claude/skills/<name>/ 等）
bash scripts/tac-check-team-status-expiry.sh
# 列出过期 + 即将过期条目；交互确认是否删除
```

清理后调用 Step 5 的提交模板。**不自动删除**——由用户确认后人工编辑文件。

## 与项目治理的对接

- **单一真理源**：`persistent-assets/governance/team-status.md`
- **跨工具入口**：`PROJECT.md` 在『全局定位』段已声明必读
- **边界遵守**：写入前必跑 Step 1 准入校验，不越界
- **Skill 不执行 git**：写文件后只打印 commit 模板
- **与相邻 skill 边界**：
  - vs `tac-experience-distill`：本 skill 沉淀"当前持续的事实"，experience-distill 沉淀"已发生的经验"
  - vs 工具私有 Memory：本 skill 跨工具/团队共享，Memory 个人不共享
  - vs 宪章/专项规范：本 skill 必有失效日（短期），宪章长期稳定

## 跨项目可移植性

本 skill 假设：

1. 仓库根有 `PROJECT.md` 作为统一入口（按 `tac-governance-project` 规范）
2. 仓库内有 `persistent-assets/governance/` 目录可放 `team-status.md`（目录可由 skill 在首次写入时自动创建）
3. 本 skill 自带 `scripts/tac-check-team-status-expiry.sh`，部署后随 skill 一并落到 `.claude/skills/<name>/scripts/` 等位置，无需依赖外部 `tac-scripts/` 目录

跨项目使用时：

- 无 `PROJECT.md` → 退化为 CLAUDE.md/AGENTS.md 引用 `persistent-assets/governance/team-status.md`
- 团队规模 <2 人 → 本 skill 不适用，引导到工具私有 Memory
