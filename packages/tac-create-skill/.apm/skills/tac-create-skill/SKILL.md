---
name: "tac-create-skill"
version: 0.4.5
description: "引导用户在 15-30 分钟内创建一个可用的 SKILL.md。当用户说'我想写 skill'/'帮我新建 skill'/'把这段流程封装成 skill'/'做个能自动 X 的 skill'/'怎么做 skill'时触发；走四步流程（场景定义 → frontmatter 设计 → 正文五要素 → 自查清单），产出可在任何兼容 Agent Skills 标准的环境下使用的 skill 目录。"
user-invocable: true
---

## 这个 Skill 做什么

把「我想写一个 skill」到「skill 目录已写完、可被加载使用」的最短路径浓缩成可执行流程。

底层 know-how 来自 [references/agent-skill-complete-guide.md](references/agent-skill-complete-guide.md) 和官方 `skill-creator`；本 skill 是它们的**精简引导版**，特化两件事：

1. **中文交互 + 结构化追问**：直接给出可填空的 frontmatter 模板与正文骨架。
2. **流程内嵌「写不出来 → 退回上一步」的硬停止**：避免用户跳过「具体使用场景」就硬写 description 导致永远不被触发。

**不做的事**：

- **不做 eval / benchmark 闭环**：需要严格触发率评测与 description 自动优化时，请用官方 `skill-creator`（含 `run_loop.py` 描述优化 + grader 评测报告）。本 skill 只到「写出可用的 SKILL.md」。
- **不绑定具体落点**：写完的 skill 放到哪个目录、是否走包管理分发、如何升级版本，都属于消费侧约定，不在本 skill 范围内。

## 何时用 / 何时不用

**用本 skill**：

- 用户说想新建 skill、想把某段流程封装成 skill、想做能自动 X 的 skill
- 已经有一段成熟的对话工作流，希望沉淀为可复用资产
- 复盘后发现「同一类需求反复出现」，决定升级为 skill

**不要用**（引导到正确入口）：

- 仅修改 / 优化已存在 skill 的 description / 触发率 → 用官方 `skill-creator` 的 description 优化循环
- 仅想了解 skill 是什么、能做什么 → 引导阅读 [references/agent-skill-complete-guide.md](references/agent-skill-complete-guide.md) 第 1-2 章
- 用户想做的事一句 prompt 就能解决 → 不需要 skill；保留在 Memory / 个人偏好里即可
- 一次性临时需求 → 不沉淀；保留在对话上下文里

## 核心约束

1. **每个 skill 必须有 2-3 个具体使用场景**。没有具体场景就写不出可触发的 description，永远不会被加载。Step 1 不通过不许进 Step 2。
2. **frontmatter 优先级 > 正文**。description 是判断「该不该加载本 skill」的唯一判据，正文再完美也救不了模糊的 description。
3. **渐进式披露**：SKILL.md ≤500 行；详细文档放 `references/<topic>.md`，私有脚本放 `scripts/`，模板 / 资源放 `assets/`。
4. **三级目录约定**：`SKILL.md` 主指令；`references/` 按需文档；`scripts/` 可执行代码；`assets/` 输出用模板。**不要**在 skill 文件夹内放 `README.md`（这是 Anthropic 标准的硬约束）。

---

## Step 1：使用场景定义（不可跳过）

**让用户回答 4 个问题，缺一不可**：

1. 这个 skill 让 Agent 能做什么？（一句话）
2. 用户会用什么短语触发？（列 3-5 个**真实表述**，不要造词）
3. 期望产物是什么？（文件类型、目录、命令输出、还是只改对话行为？）
4. 是否要打包脚本 / 模板 / 文档？（对应 scripts / assets / references）

**如果用户答不上「触发短语」**：回去问业务场景。他/她最近一次手动做这件事时是怎么开口的？把那句原话记下来——那就是触发短语。

**如果用户列不出 2-3 个具体场景**：本流程结束，引导回业务讨论。**不要硬写**——写出来的 skill 不会触发。

> 三类常见场景类别（来自 Anthropic 内部观察）：
>
> - **文档 / 资产创建**：内嵌风格指南、模板、质量检查清单
> - **工作流自动化**：分步流程 + 验证关口
> - **MCP 增强**：把 MCP 工具访问 + 领域知识合成可靠流程

更多落地模式见 [references/instruction-patterns.md](references/instruction-patterns.md)。

---

## Step 2：frontmatter 设计

**写出最小合规 frontmatter**：

```yaml
---
name: "<kebab-case-name>"
description: "<做什么>。当用户说<具体触发短语1>/<触发短语2>/<触发短语3>时触发；产物 / 落点 / 边界。"
user-invocable: true
---
```

**强制规则**：

- `name`：kebab-case，与目录名一致；禁含 `claude` / `anthropic`（保留名）；不允许空格 / 下划线 / 大写
- `description`：≤1024 字符；禁 `<` / `>`（YAML 会出现在系统提示，避免注入）；必含「做什么 + 何时用 + 触发短语」三段
- 不要包含 `README.md`（skill 文件夹内禁止）

**可选字段**：`license` / `compatibility` / `metadata`（author / version / tags 等） / `allowed-tools`。版本号 `version` 是否纳入 frontmatter、按什么节奏 bump，取决于具体消费场景的约定，**不在本 skill 强制**。

**description 三段式公式**（细节见 [references/description-and-frontmatter.md](references/description-and-frontmatter.md)）：

```text
[做什么] + [当用户说 "短语1" / "短语2" / "短语3" 时触发] + [产物 / 落点 / 边界]
```

---

## Step 3：正文五要素

按以下骨架写 SKILL.md 正文。**每个 skill 至少有这五块**：

| 五要素 | 内容 | 长度建议 |
|---|---|---|
| **何时用 / 何时不用** | 复述触发场景 + 列举不该用的相邻场景 | 5-15 行 |
| **核心约束** | 不可妥协的红线 ≤5 条 | 5-10 行 |
| **步骤** | 编号步骤；每步含「做什么 / 产物 / 验证」 | 主体 |
| **Stop conditions** | 满足即停（防越界 / 防失效） | 3-8 条 |
| **常见问题** | 现象 → 处置表 | 5-10 行 |

**写作风格**（让模型真懂而非死记）：

- 先写「为什么」再写「怎么做」。模型有 ToM，理解原因比 must / never 更可靠。
- 用祈使句、bullet、表格；少用整段散文。
- 关键约束放顶部 `## 核心约束` 段；不要埋在 Step 7 里。
- 想要确定性的检查 → 写一段脚本放 `scripts/` 并调用，**不要**指望自然语言「请验证」可靠执行。

详细模板与反模式见 [references/instruction-patterns.md](references/instruction-patterns.md)。

---

## Step 4：自查清单（产出前逐项过）

- [ ] 文件夹 kebab-case；`SKILL.md` 大小写完全一致；**不含** `README.md`
- [ ] frontmatter 有 `---` 分隔；`name` / `description` 两必备；`user-invocable: true` 建议加（启用显式调用）
- [ ] description ≤1024 字符；不含 `<` / `>`；含「做什么 + 触发短语 + 边界」三要素
- [ ] description 里每个声称的触发短语，用户都能在 Step 1 的真实场景里找到对应原话
- [ ] 正文五要素齐全：何时用 / 核心约束 / 步骤 / Stop conditions / 常见问题
- [ ] SKILL.md ≤500 行；超出内容拆 `references/`
- [ ] 私有脚本在 `scripts/`、按需文档在 `references/`、产物模板在 `assets/`
- [ ] 至少 1-2 个 Example 段落（input/output 或场景对照）

---

## Stop conditions

- Step 1 用户给不出 2-3 个具体场景 → 退回业务讨论，**不要硬写**
- Step 1 列不出真实触发短语（全是造词） → 回去问业务原话
- description 写不出具体触发短语 → 回到 Step 1
- skill 命名含 `claude` / `anthropic` 前缀 → 改名（保留名）
- SKILL.md 草稿 >500 行 → 拆 `references/<topic>.md`

## 常见问题

| 现象 | 处置 |
|---|---|
| 用户想做的事一句 prompt 就能解决 | 不需要 skill；保留在 Memory 或个人偏好里 |
| description 含「helps with X」「processes Y」类泛词 | 过于泛化；要求重写为具体场景 + 触发短语 + 边界 |
| skill 加载但模型不遵循指令 | 指令埋太深 → 关键指令上提到顶部 + `## Important` 标题 / 模糊 → 写为可执行命令 + 验证 |
| 触发不足（应该用却没自动加载） | description 不够具体或缺触发短语；加细分关键词、用户原话 |
| 触发过度（无关查询也加载） | description 太宽；加负面触发「不要用于 X」+ 收窄范围 |
| 草稿越写越长，关键点淹没 | 渐进式披露——主流程留 SKILL.md，细节拆 `references/<topic>.md` |
| skill 内固化业务红线 | 红线属于宪章 / 治理体系；skill 应「按规范执行」而非「内嵌规范」 |

## 衔接

- 完整原理（第 1-5 章）：[references/agent-skill-complete-guide.md](references/agent-skill-complete-guide.md)
- 官方深度评测 / 迭代 / description 自动优化：Anthropic `skill-creator`（含 `run_loop.py` / grader / 评测报告）
- 更多写作模板与反模式：[references/instruction-patterns.md](references/instruction-patterns.md)
- frontmatter 与 description 细则：[references/description-and-frontmatter.md](references/description-and-frontmatter.md)
