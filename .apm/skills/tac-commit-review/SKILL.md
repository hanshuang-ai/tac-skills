---
name: "tac-commit-review"
version: 0.4.5
description: "提交前自检与送审编排：校验变更范围、提交级质量门禁、暂存内容、八字段 commit message、commit 与 Gerrit refs/for 送审。当用户说'提交代码''帮我提交''准备 commit''写提交信息''commit message''八字段''git add''git commit''push''送审''Gerrit''refs/for''提交前检查'时触发。"
---

## 目标

在提交前完成一次完整的 commit 级审查：确认变更范围、执行质量门禁、暂存目标文件、生成并校验八字段提交信息，最后按项目要求提交或送审。

本 Skill 内置提交级质量门禁能力；发布/交付级准出审核仍使用 `tac-release-gate-check`。

## Step 1: 检查工作区状态

```bash
git status --short
```

1. 确认哪些文件属于本次提交主题
2. 确认是否有与当前任务无关的改动（不应带入本次提交）
3. 若同时存在多个功能/类型改动，必须拆分为多个提交

## Step 2: 提交级质量门禁

先分析已暂存和未暂存的目标变更：

```bash
git diff --cached --name-only
git diff --name-only
```

将变更文件分类：

| 分类 | 判断条件 | 后续检查 |
| ---- | -------- | -------- |
| 业务逻辑 | `src/main/**/*.kt` 或 `src/main/**/*.java`（排除资源文件） | 必须有测试 |
| 测试代码 | `src/test/**` 或 `src/androidTest/**` | 无额外检查 |
| UI/资源 | `src/main/res/**`、`AndroidManifest.xml` | 评估仪器测试 |
| 构建配置 | `build.gradle.kts`、`settings.gradle.kts`、`libs.versions.toml` | 编译验证 |
| 文档 | `persistent-assets/**/*.md`、`specs/**`、`*.md` | 无构建要求 |
| 规范 | `.specify/memory/**` | 同步检查 |

### Gate 1: 测试覆盖

**条件**：变更包含业务逻辑文件。

检查：

- 变更的每个业务逻辑文件，是否有对应测试文件存在。
- 如果变更了枚举值、公开方法签名、状态转换逻辑，是否有对应测试变更。
- 如果新增了公开类或方法，是否有对应测试。

输出：

- PASS：有匹配的测试变更，或已有充分测试覆盖。
- WARN：业务逻辑变更但无测试变更，提示需要补充或更新单元测试。
- BLOCK：新增公开 API 无任何测试，阻断提交。

### Gate 2: 文档同步

**条件**：变更了模块公开 API、枚举值、数据类字段或对外行为。

检查：

- `persistent-assets/design/_baseline/02-详细设计.md` 是否有相关接口契约。
- 若有，文档是否仍引用被变更或删除的 API 元素。
- 文档版本或设计说明是否需要同步更新。

输出：

- PASS：无关联文档，或文档已同步更新。
- WARN：存在关联文档且引用了被变更的 API，提示同步接口文档。

### Gate 3: 宪章合规

**条件**：所有变更。

检查：

- 如果变更 `.specify/memory/constitution.md`，是否更新 Sync Impact Report。
- 如果变更专项规范，主宪章中的注册是否一致。
- 如果变更涉及系统设计、新增模块或依赖变更，plan/design 是否引用工程规范。
- 如果变更涉及 Kotlin/Java 源码，是否遵循编码规范和测试要求。

输出：

- PASS：合规或不适用。
- WARN：应引用的专项规范未在 plan/design 中出现。

### Gate 4: 编译与测试验证

根据改动类型执行验证：

| 改动类型 | 必须执行 | 应评估 |
|---------|---------|--------|
| 业务逻辑 | `./gradlew testDebugUnitTest` | 仪器测试 |
| UI/资源/Manifest | `./gradlew assembleDebug` | `./gradlew lintDebug` |
| 构建配置 | `./gradlew assembleDebug` | 相关模块测试 |
| 纯文档/规范 | 无需构建 | 在交付说明中注明 |

输出：

- PASS：编译、测试或约定验证通过。
- BLOCK：编译失败、测试失败，或必须执行的验证缺失且无可接受理由。

### Gate 汇总

```markdown
## 提交级质量门禁报告

| Gate | 状态 | 说明 |
| ---- | ---- | ---- |
| 测试覆盖 | PASS / WARN / BLOCK | ... |
| 文档同步 | PASS / WARN / BLOCK | ... |
| 宪章合规 | PASS / WARN / BLOCK | ... |
| 编译与测试验证 | PASS / WARN / BLOCK | ... |

**结论**：可继续提交 / 需修复后提交
```

若任一 Gate 为 BLOCK，停止提交流程，先修复问题。只有 WARN 时，记录风险和原因后由用户决定是否继续。

## Step 3: 暂存目标文件

仅暂存本次提交的目标文件，不要使用 `git add -A`：

```bash
git add <具体文件列表>
git diff --cached --stat  # 复核暂存内容
```

## Step 4: 编写提交信息

使用八字段格式，字段之间**不得插入空行**：

```
Type=<类型> IssueId=<ID> Project=<项目> Description=<描述>
Aoe=<影响范围> RelatedModules=<关联模块> TestScope=<测试范围>
AiCodeReview=<AI审查摘要>
```

字段约束：

| 字段 | 取值/格式 | 最少字符 |
|------|----------|---------|
| Type | `需求` / `BUG` / `其他` | — |
| IssueId | BUG 编号或日期（如 `20260427`） | — |
| Project | `ALL` 或项目代号 | — |
| Description | 中文概要 | — |
| Aoe | 影响范围 | — |
| RelatedModules | 关联模块 | 2 |
| TestScope | 测试范围 | 15 |
| AiCodeReview | AI 审查摘要 | 10（中文） |

### 字段值书写禁忌（防 server-side hook 拒推）

server-side hook 按 `^字段名=` 模式扫描整段 message 计数，**长文本字段的值里出现 `字段名=...` 字面**会被当成"第二个该字段"，触发 `[ERROR]配置项重复` 拒绝整个 push（本地 `tac-check-commit-format.sh` 不拦截，必到 Gerrit 才暴露）。

**禁止形式**（典型踩坑）：

| 字段 | 禁止写法 | 推荐写法 |
|------|---------|---------|
| Description / AiCodeReview | `...属于Type=其他类...` | `...属"其他"分类...` |
| AiCodeReview | `...遵循Aoe=纯文档原则...` | `...遵循"纯文档"原则...` |
| 任意长字段 | 任何引用 `Type=` / `IssueId=` / `Project=` / `Description=` / `Aoe=` / `RelatedModules=` / `TestScope=` / `AiCodeReview=` 字面值 | 用引号、引述、自然语言描述代替 |

**自检命令（Step 5 之前先跑）：**

```bash
for f in Type= IssueId= Project= Description= Aoe= RelatedModules= TestScope= AiCodeReview=; do
  n=$(grep -oE "$f" <commit-msg-file> | wc -l | tr -d ' ')
  [ "$n" -ne 1 ] && echo "字段重复或缺失: $f 出现 $n 次"
done
```

每个字段名应**恰好出现 1 次**，否则 hook 必拒。

### URL 编码字符（`%`）规避

commit message 中尽量避免出现 `%` 字符（如 `git log --format=%an`），原因：Gerrit push URL 用 `%` 作为参数分隔（`%t=<hashtag>`），部分版本 hook 会对 message 中的 `%` 做二次解析造成歧义。如必须提及，改写为不含 `%` 的等价描述（如 `--format-an-cd`）。

## Step 5: 辅助脚本校验

如果可用，运行格式校验脚本：

```bash
# 路径相对于本 SKILL.md 所在目录（部署后位于 .claude/skills/<name>/ 等）
bash scripts/tac-check-commit-format.sh <commit-msg-file>
```

## Step 6: 提交

```bash
git commit
```

## Step 7: 提交后复核

```bash
git log -1 --pretty=%B          # 确认提交信息
git cat-file -p HEAD            # 确认最终 message 结构（无错位）
git status --short              # 确认剩余未提交改动
```

## Step 8: 推送送审（如需）

对 Gerrit 仓库，默认送审而非直推：

```bash
git push origin <本地分支>:refs/for/<target-branch>%t=<hashtag>
# <target-branch>：项目 Gerrit 实例上要合入的远程分支名（通常是 master 或自定义 review 分支，按项目实际填写）
```

Hashtag 候选值：`模块内部基础` / `模块交互` / `模块架构` / `系统架构` / `other`

## 自检清单

- [ ] 变更范围确认：只包含本次主题的文件
- [ ] 提交级质量门禁已执行，且无 BLOCK
- [ ] 验证命令已执行（或记录未执行原因）
- [ ] 测试覆盖、文档同步、宪章合规已检查
- [ ] 提交信息八字段完整、连续、无空行
- [ ] Type 取值正确（需求/BUG/其他）
- [ ] TestScope >= 15 字符，AiCodeReview >= 10 中文字符
- [ ] **字段名各出现且仅出现 1 次**（长文本字段值里禁止 `字段名=值` 字面引用，否则 server-side hook 拒推 `[ERROR]配置项重复`）
- [ ] commit message 不含 `%` 字符（与 Gerrit push URL 的 `%t=hashtag` 冲突）
- [ ] 推送目标为 `refs/for/<branch>`（非直推）
