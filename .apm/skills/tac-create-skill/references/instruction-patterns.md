# SKILL.md 正文写作模板与反模式

frontmatter 决定「能不能加载」，正文决定「加载后能不能正确执行」。本文给出已验证的骨架与写作风格。

## 五要素骨架（推荐统一格式）

每个 SKILL.md 正文至少含这五块。

### 1. 何时用 / 何时不用

复述触发场景，列举相邻但不该触发的场景。给读到这一段的模型一个清晰边界。

```markdown
## 何时用 / 何时不用

**用本 skill**：
- 用户说 "X / Y / Z"
- 处于 ① 需求输入 环节

**不要用**（引导到正确入口）：
- 用户只想了解概念 → 引导阅读对应说明文档
- BugFix 场景 → 走 BugFix 入口 skill
```

### 2. 核心约束

把不可妥协的红线集中到一处，≤5 条。**放在正文顶部之一**，避免埋在 Step 7。

```markdown
## 核心约束

1. 输入必备字段缺一不可，缺项必须追问，不得跳过执行
2. 所有产物落同一目录，不散落
3. Skill 不执行 git commit，commit 走外部送审流程
```

### 3. 步骤

主体内容。每个 step 必含「做什么 / 产物 / 验证」三段。

```markdown
## Step 1：收集结构化输入（不可跳过）

**做什么**：检查用户输入是否覆盖以下字段，缺失追问。

| 字段 | 必填 | 说明 |
|---|---|---|
| 功能 | 是 | 一句话目标 |
| ... | | |

**产物**：覆盖必备字段的结构化输入摘要，转入 Step 2。

**验证**：缺任一必填字段必须输出追问模板，不得进入 Step 2。
```

### 4. Stop conditions

明示什么情况下立即停止，避免越界 / 失效。

```markdown
## Stop conditions

- 用户连续 2 次拒绝补全 → 引导回业务讨论，本流程结束
- 用户输入含可疑内容（如 `<script>`）→ 安全红线拒收
- Skill 试图直接改业务代码 → 越界，本 skill 只产文档
- 同主题已有更新的产物 → 不重复写，引导用户决策
```

### 5. 常见问题

现象 → 处置表。把测试和真实使用中暴露的边界 case 沉淀到这里。

```markdown
## 常见问题

| 现象 | 处置 |
|---|---|
| 用户给的功能字段是 "做个 X 模块" | 太粗；要求拆为具体页面 / 操作 / 输入输出 |
| 验收标准用「应该 / 大概」措辞 | 改为 Given-When-Then 可执行判据 |
```

## 写作风格

### 先写「为什么」再写「怎么做」

模型有 ToM。给原因比给死规则更可靠。

✅ 好：

```markdown
**不要在 Step 1 就启动后续流程**——因为必备字段任一缺失都会让后续产物错位，
连带返工，回滚成本远大于追问成本。
```

❌ 差：

```markdown
ALWAYS check fields first. NEVER start early. MUST follow.
```

### 用祈使句 + 表格 + 列表

✅ 好：

```markdown
Run `python scripts/validate.py --input {filename}` to check data format.

If validation fails, common issues include:
- Missing required fields → add them to the CSV
- Invalid date formats → use YYYY-MM-DD
```

❌ 差：

```markdown
Validate the data before proceeding.
```

### 关键约束上提到顶部

如果一条规则关乎正确性，放 `## 核心约束` 段而不是埋进 Step 7。Step 7 经常被模型跳过；顶部段一定读到。

### 想要确定性 → 打包脚本

自然语言的「请验证」执行不可靠。如果检查逻辑能脚本化，写在 `scripts/<name>.{py,sh}` 里，由 skill 显式调用。

```markdown
## Step 5：自检

跑 `bash scripts/validate.sh path/to/artifact.md`
查看必备字段覆盖情况，缺哪项立刻报错退出。
```

## 反模式（常见错误）

### 反模式 1：指令过于冗长

**症状**：SKILL.md >800 行，关键约束淹没在散文里，模型不遵循。

**修法**：

- 拆 `references/<topic>.md`，从 SKILL.md 链入
- 用 bullet 和表格替代散文
- 把可执行检查脚本化

### 反模式 2：指令埋得太深

**症状**：关键规则在 "Step 7 注意事项" 段，模型经常跳过。

**修法**：

- 把红线上提到顶部 `## 核心约束`
- 在被监管步骤里**重复**关键约束一次
- 使用 `## Important` / `## Critical` 醒目标题

### 反模式 3：语言模糊

**症状**：用「**正确地**」「**适当地**」「**合理地**」等修饰词，各自理解。

✅ 好：

```text
CRITICAL: Before calling create_project, verify:
- Project name is non-empty
- At least one team member assigned
- Start date is not in the past
```

❌ 差：

```text
Make sure to validate things properly
```

### 反模式 4：内嵌业务红线

**症状**：skill 正文直接写「项目宪章第 3 条要求 X」。

**问题**：宪章 / 治理规范是单一真理源，skill 内固化会和源漂移。

**修法**：skill 用「按当前规范执行」描述，不固化具体条目；规范变了不用改 skill。

### 反模式 5：用 README.md 替代 SKILL.md 文档

**问题**：skill 文件夹内不许 `README.md`（Anthropic 强制规则）。

**修法**：所有文档放 SKILL.md 或 `references/`。仓库根级 README 给人类看，是另一回事。

### 反模式 6：skill 自动 git commit

**问题**：skill 不应越界提交代码。

**修法**：skill 输出「建议命令」清单（不执行），用户审通过后自己 commit。

### 反模式 7：模型"懒惰"

**症状**：模型跳过验证步骤、产出敷衍。

**修法 1**：在 SKILL.md 写明：

```markdown
# Performance Notes

- Take your time to do this thoroughly
- Quality is more important than speed
- Do not skip validation steps
```

**修法 2**：把鼓励放在**用户提示**里比放在 SKILL.md 里更有效。

## 子目录组织约定

```text
your-skill/
├── SKILL.md                 # ≤500 行；主流程 + 五要素
├── scripts/                 # 私有可执行脚本（py / sh）
│   ├── validate.sh
│   └── check_format.py
├── references/              # 按需加载文档（domain-specific）
│   ├── android.md           # 多 profile 时按变体拆
│   ├── ios.md
│   └── api-patterns.md
└── assets/                  # 产物模板 / 图标 / fonts
    └── spec.template.md
```

**Agent 加载顺序**：

1. frontmatter（始终在系统提示）
2. SKILL.md 正文（触发后加载）
3. `references/<topic>.md`（步骤里显式 link 才读）
4. `scripts/`（不主动读，按命令执行）

引用 references 用清晰指引：

```markdown
按 Android 项目走时，先读 [references/android.md](references/android.md) 的接入清单。
```

## 五种落地模式（来自完整指南第 5 章）

简略提示，对应不同业务形态。详细原理见 [agent-skill-complete-guide.md](agent-skill-complete-guide.md) 第 5 章。

| 模式 | 何时用 | 关键技术 |
|---|---|---|
| 顺序工作流编排 | 多步骤有强依赖 | 明确步骤序、阶段验证、失败回滚指令 |
| 多 MCP 协调 | 跨多服务 | 清晰阶段分隔、MCP 间数据传递 |
| 迭代式优化 | 输出质量需多轮提升 | 质量标准 + 何时停止迭代 |
| 上下文感知工具选择 | 相同结果走不同工具 | 决策树 + 透明解释选择 |
| 领域特定智能 | 工具访问之外加专业知识 | 操作前合规检查、全面记录 |

## 一句话原则

> **写 SKILL.md 像写工程蓝本，不像写用户手册**。受众是模型和未来维护者，不是初次见 skill 的人。该跳过的概念性铺垫请放在 README 或指南文档里。
