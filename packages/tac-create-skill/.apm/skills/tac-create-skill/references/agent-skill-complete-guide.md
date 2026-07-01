# Agent Skill 构建完整指南

Skill 是一组指令，它以一个简单文件夹的形式打包，用来教 Claude 如何处理特定任务或工作流。Skill 是按照你的具体需求定制 Claude 的最强方式之一。你不必在每次对话中重复解释自己的偏好、流程和领域知识，Skill 让你只教 Claude 一次，之后每次都能受益。

当你有可重复的工作流时，Skill 会非常有用：根据规格生成前端设计、用一致的方法开展研究、创建符合团队风格指南的文档，或编排多步骤流程。它们能很好地配合 Claude 内置能力，例如代码执行和文档创建。对于正在构建 MCP 集成的人来说，Skill 还能增加一个强大的层级，帮助把原始工具访问转化为可靠、优化过的工作流。

本指南涵盖构建有效 Skill 所需了解的全部内容，从规划、结构到测试和分发。无论你是为自己、团队还是社区构建 Skill，都能在其中找到实用模式和真实示例。

### 你将学到什么

- Skill 结构的技术要求和最佳实践
- 独立 Skill 与 MCP 增强工作流的模式
- 我们在不同使用场景中看到的有效模式
- 如何测试、迭代和分发你的 Skill

### 适合谁阅读

- 希望 Claude 一致遵循特定工作流的开发者
- 希望 Claude 遵循特定工作流的高级用户
- 希望在组织内标准化 Claude 使用方式的团队

### 阅读本指南的两条路径

构建独立 Skill？重点阅读“基础知识”“规划与设计”以及第 1、2 类场景。增强 MCP 集成？“Skills + MCP”部分和第 3 类场景更适合你。这两条路径共享相同的技术要求，你可以根据自己的使用场景选择相关内容。

### 阅读后的收获

读完之后，你将能够在一次工作会话中构建一个可用的 Skill。使用 skill-creator 构建并测试第一个可工作的 Skill，预计需要 15 到 30 分钟。

让我们开始。

## 第 1 章 基础知识

### 什么是 Skill？

Skill 是一个包含以下内容的文件夹：

- **SKILL.md（必需）**：带有 YAML frontmatter 的 Markdown 指令
- **scripts/（可选）**：可执行代码，例如 Python、Bash 等
- **references/（可选）**：按需加载的文档
- **assets/（可选）**：输出中使用的模板、字体、图标

![一个简单的 SKILL.md 文件](assets/claude-skill-guide/simple-skill-md.png)

### 核心设计原则

#### 渐进式披露

Skill 使用三级系统：

- **第一层级（YAML frontmatter）**：始终加载到 Claude 的系统提示中。它提供足够的信息，让 Claude 知道何时应该使用某个 Skill，同时避免把全部内容都加载进上下文。
- **第二层级（SKILL.md 正文）**：当 Claude 认为该 Skill 与当前任务相关时加载。它包含完整指令和指导。
- **第三层级（链接文件）**：Skill 目录内打包的其他文件，Claude 可以仅在需要时选择导航和发现。

![Skill 的三级加载层级与 token 预算](assets/claude-skill-guide/skill-context-levels.png)

这种渐进式披露能在保持专业能力的同时尽量减少 token 使用量。

![Skill 与上下文窗口的关系](assets/claude-skill-guide/skills-context-window.png)

#### 可组合性

Claude 可以同时加载多个 Skill。你的 Skill 应该能与其他 Skill 良好协作，而不应假设自己是唯一可用能力。

#### 可移植性

Skill 在 Claude.ai、Claude Code 和 API 中的工作方式一致。只要环境支持 Skill 所需的依赖，就可以一次创建 Skill，并在所有界面中无修改使用。

### 给 MCP 构建者：Skills + Connectors

> 构建不带 MCP 的独立 Skill？可以跳到“规划与设计”，之后随时回来阅读本节。

如果你已经有一个可用的 MCP server，最难的部分已经完成。Skill 是其上的知识层，用来捕获你已经掌握的工作流和最佳实践，让 Claude 能稳定应用它们。

### 厨房类比

MCP 提供专业厨房：工具、食材和设备的访问能力。

Skill 提供菜谱：关于如何创造有价值产出的分步指令。

二者结合之后，用户就能完成复杂任务，而不必自己搞清每一步。

### 它们如何协同工作

| MCP（连接能力） | Skills（知识） |
| --- | --- |
| 将 Claude 连接到你的服务，例如 Notion、Asana、Linear 等 | 教 Claude 如何有效使用你的服务 |
| 提供实时数据访问和工具调用 | 捕获工作流和最佳实践 |
| Claude 能做什么 | Claude 应该如何做 |

### 这对你的 MCP 用户为什么重要

#### 没有 Skill 时

- 用户连接了你的 MCP，却不知道下一步做什么
- 支持工单会反复询问“我如何用你的集成完成 X”
- 每次对话都从零开始
- 用户每次提示方式不同，导致结果不一致
- 用户可能责怪你的 connector，但真实问题是缺少工作流指导

#### 有 Skill 时

- 预构建工作流会在需要时自动激活
- 工具使用更一致、更可靠
- 每次交互都内嵌最佳实践
- 降低用户学习你的集成的门槛

## 第 2 章 规划与设计

### 从使用场景开始

在编写任何代码之前，先确定你的 Skill 应该支持的 2 到 3 个具体使用场景。

#### 好的使用场景定义

```text
Use Case: Project Sprint Planning
Trigger: User says "help me plan this sprint" or "create sprint tasks"
Steps:
1. Fetch current project status from Linear (via MCP)
2. Analyze team velocity and capacity
3. Suggest task prioritization
4. Create tasks in Linear with proper labels and estimates
Result: Fully planned sprint with tasks created
```

### 问问自己

- 用户想完成什么？
- 这需要哪些多步骤工作流？
- 需要哪些工具，内置工具还是 MCP？
- 应该内嵌哪些领域知识或最佳实践？

### 常见 Skill 使用场景类别

在 Anthropic，我们观察到三类常见使用场景。

#### 类别 1：文档与资产创建

**用于**：创建一致、高质量的输出，包括文档、演示文稿、应用、设计、代码等。

**真实示例**：frontend-design skill，也可参考 docx、pptx、xlsx 和 ppt 相关 Skill。

> “创建有辨识度、生产级的前端界面，并具备高设计质量。用于构建 Web 组件、页面、artifact、海报或应用。”

**关键技术：**

- 内嵌风格指南和品牌标准
- 使用模板结构保持输出一致
- 最终交付前使用质量检查清单
- 不需要外部工具，使用 Claude 内置能力

### 类别 2：工作流自动化

**用于**：受益于一致方法论的多步骤流程，包括跨多个 MCP server 的协调。

**真实示例**：skill-creator skill

> “用于创建新 Skill 的交互式指南。引导用户完成使用场景定义、frontmatter 生成、指令编写和验证。”

**关键技术：**

- 带验证关口的分步工作流
- 常见结构模板
- 内置审查和改进建议
- 迭代式优化循环

### 类别 3：MCP 增强

**用于**：为 MCP server 提供的工具访问增加工作流指导。

**真实示例**：来自 Sentry 的 sentry-code-review skill

> “使用 Sentry 通过其 MCP server 提供的错误监控数据，自动分析并修复 GitHub Pull Request 中检测到的 bug。”

**关键技术：**

- 按顺序协调多次 MCP 调用
- 内嵌领域专业知识
- 提供用户原本需要手动说明的上下文
- 处理常见 MCP 问题

### 定义成功标准

你如何知道自己的 Skill 正在正常工作？

这些是理想目标，属于粗略基准，而不是精确阈值。目标应尽量严谨，但也要接受其中会包含一些基于感受的评估。我们正在积极开发更强健的度量指导和工具。

#### 定量指标

- **Skill 在 90% 的相关查询中触发**
  - 衡量方式：运行 10 到 20 个应该触发该 Skill 的测试查询。记录它自动加载的次数，以及需要显式调用的次数。
- **用 X 次工具调用完成工作流**
  - 衡量方式：比较启用 Skill 与未启用 Skill 时完成同一任务的表现。统计工具调用次数和总 token 消耗。
- **每个工作流 0 次失败 API 调用**
  - 衡量方式：在测试运行期间监控 MCP server 日志。追踪重试率和错误码。

#### 定性指标

- **用户不需要提示 Claude 下一步怎么做**
  - 评估方式：测试时记录你需要重定向或澄清的频率。向 beta 用户收集反馈。
- **工作流无需用户纠正即可完成**
  - 评估方式：同一请求运行 3 到 5 次。比较输出在结构一致性和质量上的表现。
- **跨会话结果一致**
  - 评估方式：新用户能否在几乎无需指导的情况下第一次就完成任务？

### 技术要求

### 文件结构

```text
your-skill-name/
├── SKILL.md              # 必需，主 Skill 文件
├── scripts/              # 可选，可执行代码
│   ├── process_data.py   # 示例
│   └── validate.sh       # 示例
├── references/           # 可选，文档
│   ├── api-guide.md      # 示例
│   └── examples/         # 示例
└── assets/               # 可选，模板等
    └── report-template.md # 示例
```

![在 Skill 中打包可执行脚本](assets/claude-skill-guide/bundling-executable-scripts.png)

### 关键规则

#### SKILL.md 命名

- 必须精确命名为 **SKILL.md**，区分大小写
- 不接受任何变体，例如 SKILL.MD、skill.md 等

#### Skill 文件夹命名

- 使用 kebab-case：`notion-project-setup` ✅
- 不使用空格：`Notion Project Setup` ❌
- 不使用下划线：`notion_project_setup` ❌
- 不使用大写字母：`NotionProjectSetup` ❌

#### 不要包含 README.md

- 不要在 Skill 文件夹内包含 README.md
- 所有文档放在 SKILL.md 或 references/ 中
- 注意：通过 GitHub 分发时，你仍然会需要一个仓库级 README 给人类用户阅读。参见“分发与共享”。

### YAML frontmatter：最重要的部分

YAML frontmatter 是 Claude 判断是否加载你的 Skill 的依据。这里必须写对。

#### 最小必需格式

```yaml
---
name: your-skill-name
description: What it does. Use when user asks to [specific phrases].
---
```

这就是开始所需的全部内容。

### 字段要求

#### name（必需）

- 只能使用 kebab-case
- 不允许空格或大写字母
- 应该与文件夹名一致

#### description（必需）

- 必须同时包含：
  - Skill 做什么
  - 何时使用它，也就是触发条件
- 少于 1024 个字符
- 不包含 XML 标签，例如 `<` 或 `>`
- 包含用户可能会说的具体任务
- 如果相关，提到文件类型

### license（可选）

- 如果要将 Skill 开源，可以使用
- 常见值：MIT、Apache-2.0

### compatibility（可选）

- 1 到 500 个字符
- 表明环境要求，例如目标产品、所需系统包、网络访问需求等

### metadata（可选）

- 任意自定义键值对
- 建议字段：author、version、mcp-server
- 示例：

```yaml
metadata:
  author: ProjectHub
  version: 1.0.0
  mcp-server: projecthub
```

### 安全限制

#### frontmatter 中禁止出现

- XML 尖括号：`<`、`>`
- 名称中包含 `claude` 或 `anthropic` 的 Skill，这些名称已保留

**原因**：frontmatter 会出现在 Claude 的系统提示中。恶意内容可能注入指令。

### 编写有效的 Skill

### description 字段

根据 Anthropic 工程博客的说法：“这些元数据提供刚好足够的信息，让 Claude 知道何时应该使用每个 Skill，而无需把它的全部内容加载进上下文。”这是渐进式披露的第一层级。

#### 结构

```text
[What it does] + [When to use it] + [Key capabilities]
```

#### 好的 description 示例

```yaml
# Good - specific and actionable
description: Analyzes Figma design files and generates developer handoff documentation. Use when user uploads .fig files, asks for "design specs", "component documentation", or "design-to-code handoff".

# Good - includes trigger phrases
description: Manages Linear project workflows including sprint planning, task creation, and status tracking. Use when user mentions "sprint", "Linear tasks", "project planning", or asks to "create tickets".

# Good - clear value proposition
description: End-to-end customer onboarding workflow for PayFlow. Handles account creation, payment setup, and subscription management. Use when user says "onboard new customer", "set up subscription", or "create PayFlow account".
```

### 不好的 description 示例

```yaml
# Too vague
description: Helps with projects.

# Missing triggers
description: Creates sophisticated multi-page documentation systems.

# Too technical, no user triggers
description: Implements the Project entity model with hierarchical relationships.
```

### 编写主指令

frontmatter 之后，编写实际的 Markdown 指令。

#### 推荐结构

根据你的 Skill 调整这个模板。用你的具体内容替换方括号中的部分。

````markdown
---
name: your-skill
description: [--.]
---

# Your Skill Name

## Instructions

### Step 1: [First Major Step]

Clear explanation of what happens.

Example:

```bash
python scripts/fetch_data.py --project-id PROJECT_ID
```

Expected output: [describe what success looks like]

(Add more steps as needed)

## Examples

### Example 1: [common scenario]

User says: "Set up a new marketing campaign"

Actions:
1. Fetch existing campaigns via MCP
2. Create new campaign with provided parameters

Result: Campaign created with confirmation link

(Add more examples as needed)

## Troubleshooting

### Error: [Common error message]

Cause: [Why it happens]

Solution: [How to fix]

(Add more error cases as needed)
````

### 指令最佳实践

### 具体且可执行

✅ 好：

```text
Run `python scripts/validate.py --input {filename}` to check data format.

If validation fails, common issues include:
- Missing required fields (add them to the CSV)
- Invalid date formats (use YYYY-MM-DD)
```

❌ 差：

```text
Validate the data before proceeding.
```

### 包含错误处理

```markdown
# Common Issues

## MCP Connection Failed

If you see "Connection refused":
1. Verify MCP server is running: Check Settings > Extensions
2. Confirm API key is valid
3. Try reconnecting: Settings > Extensions > [Your Service] > Reconnect
```

### 清楚引用打包资源

```text
Before writing queries, consult `references/api-patterns.md` for:
- Rate limiting guidance
- Pagination patterns
- Error codes and handling
```

### 使用渐进式披露

让 SKILL.md 聚焦于核心指令。把详细文档移动到 `references/` 并链接它们。关于三级系统如何工作，参见“核心设计原则”。

![通过 references 打包更多内容](assets/claude-skill-guide/bundling-additional-content.png)

## 第 3 章 测试与迭代

Skill 可以按不同严格程度进行测试，具体取决于你的需求：

- **在 Claude.ai 中手动测试**：直接运行查询并观察行为。迭代速度快，无需设置。
- **在 Claude Code 中脚本化测试**：自动化测试用例，使变更验证可重复。
- **通过 Skills API 进行程序化测试**：构建评估套件，针对定义好的测试集系统化运行。

选择与你的质量要求和 Skill 可见范围相匹配的方法。一个小团队内部使用的 Skill，与部署给数千名企业用户的 Skill，测试需求不同。

### 专业提示：先在单一任务上迭代，再扩展

我们发现，最有效的 Skill 创建者会先围绕一个有挑战的单一任务反复迭代，直到 Claude 成功，然后把获胜方法提炼成 Skill。这利用了 Claude 的上下文学习能力，相比宽泛测试能更快得到信号。一旦有了可工作的基础，再扩展到多个测试用例以提升覆盖面。

### 推荐测试方法

根据早期经验，有效的 Skill 测试通常覆盖三个方面。

#### 1. 触发测试

**目标**：确保你的 Skill 在正确时机加载。

**测试用例：**

- ✅ 在明显任务上触发
- ✅ 在改述后的请求上触发
- ❌ 在无关主题上不触发

**示例测试套件：**

应该触发：

```text
"Help me set up a new ProjectHub workspace"
"I need to create a project in ProjectHub"
"Initialize a ProjectHub project for Q4 planning"
```

不应该触发：

```text
"What's the weather in San Francisco?"
"Help me write Python code"
"Create a spreadsheet" (unless ProjectHub skill handles sheets)
```

### 2. 功能测试

**目标**：验证 Skill 生成正确输出。

**测试用例：**

- 生成有效输出
- API 调用成功
- 错误处理有效
- 覆盖边界情况

**示例：**

```text
Test: Create project with 5 tasks
Given: Project name "Q4 Planning", 5 task descriptions
When: Skill executes workflow
Then:
  - Project created in ProjectHub
  - 5 tasks created with correct properties
  - All tasks linked to project
  - No API errors
```

### 3. 性能对比

**目标**：证明该 Skill 相比基线改进了结果。

使用“定义成功标准”中的指标。下面是一个可能的对比。

**基线对比：**

未使用 Skill：

- 用户每次都提供指令
- 15 轮来回消息
- 3 次失败 API 调用需要重试
- 消耗 12,000 token

使用 Skill：

- 自动执行工作流
- 仅 2 个澄清问题
- 0 次失败 API 调用
- 消耗 6,000 token

### 使用 skill-creator Skill

skill-creator Skill 可通过 Claude.ai 的插件目录使用，也可下载后供 Claude Code 使用，它能帮助你构建和迭代 Skill。如果你有一个 MCP server，并且知道最重要的 2 到 3 个工作流，通常可以在一次工作会话中构建并测试一个可用 Skill，耗时常为 15 到 30 分钟。

#### 创建 Skill

- 根据自然语言描述生成 Skill
- 生成格式正确、包含 frontmatter 的 SKILL.md
- 建议触发短语和结构

#### 审查 Skill

- 标记常见问题，例如描述含糊、缺少触发条件、结构问题
- 识别潜在的过度触发或触发不足风险
- 根据 Skill 声明的用途建议测试用例

#### 迭代改进

- 使用 Skill 并遇到边界情况或失败之后，把这些示例带回 skill-creator
- 示例：“使用本次对话中识别的问题与解决方案，改进该 Skill 处理 [specific edge case] 的方式。”

### 使用方式

```text
"Use the skill-creator skill to help me build a skill for [your use case]"
```

注意：skill-creator 能帮助你设计和优化 Skill，但不会执行自动化测试套件，也不会生成定量评估结果。

### 基于反馈迭代

Skill 是会持续演进的文档。请计划基于以下信号进行迭代。

#### 触发不足信号

- Skill 在应该加载时没有加载
- 用户手动启用它
- 支持问题集中在何时使用它

**解决方案**：在 description 中增加更多细节和细微差别，这可能包括关键词，尤其是技术术语。

#### 过度触发信号

- Skill 针对无关查询加载
- 用户禁用它
- 用户对用途感到困惑

**解决方案**：添加负面触发条件，并写得更具体。

#### 执行问题

- 结果不一致
- API 调用失败
- 需要用户纠正

**解决方案**：改进指令，添加错误处理。

## 第 4 章 分发与共享

Skill 让你的 MCP 集成更完整。当用户比较 connector 时，带有 Skill 的方案能更快体现价值，因此相比只有 MCP 的替代方案更有优势。

### 当前分发模型（2026 年 1 月）

#### 个人用户如何获取 Skill

1. 下载 Skill 文件夹
2. 如有需要，将文件夹压缩成 zip
3. 通过 Claude.ai 的 Settings > Capabilities > Skills 上传
4. 或放入 Claude Code 的 skills 目录

#### 组织级 Skill

- 管理员可以在整个工作区部署 Skill，该能力于 2025 年 12 月 18 日发布
- 自动更新
- 集中管理

### 开放标准

我们已经将 Agent Skills 发布为开放标准。像 MCP 一样，我们相信 Skill 应该能跨工具和平台移植，同一个 Skill 应该无论在 Claude 还是其他 AI 平台中都能工作。与此同时，一些 Skill 被设计为充分利用某个特定平台的能力，作者可以在 compatibility 字段中说明这一点。我们一直在与生态系统成员协作推进这一标准，并对早期采用感到兴奋。

### 通过 API 使用 Skill

对于程序化使用场景，例如构建利用 Skill 的应用、agent 或自动化工作流，API 提供对 Skill 管理和执行的直接控制。

#### 关键能力

- 用于列出和管理 Skill 的 `/v1/skills` endpoint
- 通过 `container.skills` 参数把 Skill 添加到 Messages API 请求中
- 通过 Claude Console 进行版本控制和管理
- 与 Claude Agent SDK 配合，用于构建自定义 agent

#### 何时通过 API 使用 Skill，何时使用 Claude.ai

| 使用场景 | 最佳界面 |
| --- | --- |
| 终端用户直接与 Skill 交互 | Claude.ai / Claude Code |
| 开发期间的手动测试和迭代 | Claude.ai / Claude Code |
| 个人、临时工作流 | Claude.ai / Claude Code |
| 程序化使用 Skill 的应用 | API |
| 大规模生产部署 | API |
| 自动化流水线和 agent 系统 | API |

### 注意

API 中的 Skill 需要 Code Execution Tool beta，它提供 Skill 运行所需的安全环境。

有关实现细节，参见：

- Skills API Quickstart
- Create Custom skills
- Skills in the Agent SDK

### 当前推荐做法

先将你的 Skill 托管在 GitHub 上，使用公开仓库、清晰的 README（给人类访问者阅读，这与 Skill 文件夹不同，Skill 文件夹内不应包含 README.md），并提供带截图的示例用法。然后在 MCP 文档中增加一个部分，链接到该 Skill，解释两者一起使用的价值，并提供快速入门指南。

1. **托管到 GitHub**
   - 为开源 Skill 创建公开仓库
   - README 中包含清晰安装说明
   - 提供示例用法和截图
2. **写入你的 MCP 仓库文档**
   - 从 MCP 文档链接到 Skill
   - 解释二者一起使用的价值
   - 提供快速入门指南
3. **创建安装指南**

````markdown
# Installing the [Your Service] skill

1. Download the skill:
   - Clone repo: `git clone https://github.com/yourcompany/skills`
   - Or download ZIP from Releases
2. Install in Claude:
   - Open Claude.ai > Settings > skills
   - Click "Upload skill"
   - Select the skill folder (zipped)
3. Enable the skill:
   - Toggle on the [Your Service] skill
   - Ensure your MCP server is connected
4. Test:
   - Ask Claude: "Set up a new project in [Your Service]"
````

### 定位你的 Skill

你如何描述 Skill，会决定用户是否理解它的价值并真正尝试使用它。在 README、文档或营销材料中介绍 Skill 时，请记住以下原则。

#### 聚焦结果，而非功能

✅ 好：

```text
"The ProjectHub skill enables teams to set up complete project workspaces in seconds, including pages, databases, and templates, instead of spending 30 minutes on manual setup."
```

❌ 差：

```text
"The ProjectHub skill is a folder containing YAML frontmatter and Markdown instructions that calls our MCP server tools."
```

#### 突出 MCP + Skill 的组合叙事

```text
"Our MCP server gives Claude access to your Linear projects.
Our skills teach Claude your team's sprint planning workflow.
Together, they enable AI-powered project management."
```

## 第 5 章 模式与故障排查

这些模式来自早期采用者和内部团队创建的 Skill。它们代表我们看到的常见有效方法，而不是强制模板。

### 选择你的方法：问题优先或工具优先

可以把它想象成去 Home Depot。你可能带着一个问题走进去：“我需要修好厨房柜子”，然后员工会指引你找到合适工具。你也可能先挑了一把新电钻，再询问如何把它用于自己的具体工作。

Skill 的工作方式也类似：

- **问题优先**：“我需要设置一个项目工作区” -> 你的 Skill 以正确顺序编排合适的 MCP 调用。用户描述结果，Skill 处理工具。
- **工具优先**：“我已经连接了 Notion MCP” -> 你的 Skill 教 Claude 最优工作流和最佳实践。用户已有访问能力，Skill 提供专业知识。

多数 Skill 会偏向其中一个方向。知道哪种框架适合你的使用场景，有助于你选择下面的正确模式。

### 模式 1：顺序工作流编排

**使用时机**：用户需要按特定顺序执行多步骤流程。

**示例结构：**

```markdown
# Workflow: Onboard New Customer

## Step 1: Create Account
Call MCP tool: `create_customer`
Parameters: name, email, company

## Step 2: Setup Payment
Call MCP tool: `setup_payment_method`
Wait for: payment method verification

## Step 3: Create Subscription
Call MCP tool: `create_subscription`
Parameters: plan_id, customer_id (from Step 1)

## Step 4: Send Welcome Email
Call MCP tool: `send_email`
Template: welcome_email_template
```

**关键技术：**

- 明确步骤顺序
- 步骤之间存在依赖关系
- 每个阶段都有验证
- 为失败情况提供回滚指令

### 模式 2：多 MCP 协调

**使用时机**：工作流跨多个服务。

**示例：设计到开发交接**

```markdown
## Phase 1: Design Export (Figma MCP)
1. Export design assets from Figma
2. Generate design specifications
3. Create asset manifest

## Phase 2: Asset Storage (Drive MCP)
1. Create project folder in Drive
2. Upload all assets
3. Generate shareable links

## Phase 3: Task Creation (Linear MCP)
1. Create development tasks
2. Attach asset links to tasks
3. Assign to engineering team

## Phase 4: Notification (Slack MCP)
1. Post handoff summary to #engineering
2. Include asset links and task references
```

**关键技术：**

- 清晰的阶段分隔
- MCP 之间的数据传递
- 进入下一阶段前先验证
- 集中式错误处理

### 模式 3：迭代式优化

**使用时机**：输出质量会通过迭代提升。

**示例：报告生成**

```markdown
# Iterative Report Creation

## Initial Draft
1. Fetch data via MCP
2. Generate first draft report
3. Save to temporary file

## Quality Check
1. Run validation script: `scripts/check_report.py`
2. Identify issues:
   - Missing sections
   - Inconsistent formatting
   - Data validation errors

## Refinement Loop
1. Address each identified issue
2. Regenerate affected sections
3. Re-validate
4. Repeat until quality threshold met

## Finalization
1. Apply final formatting
2. Generate summary
3. Save final version
```

**关键技术：**

- 明确质量标准
- 迭代改进
- 验证脚本
- 知道何时停止迭代

### 模式 4：上下文感知的工具选择

**使用时机**：相同结果会根据上下文使用不同工具。

**示例：文件存储**

```markdown
# Smart File Storage

## Decision Tree
1. Check file type and size
2. Determine best storage location:
   - Large files (>10MB): Use cloud storage MCP
   - Collaborative docs: Use Notion/Docs MCP
   - Code files: Use GitHub MCP
   - Temporary files: Use local storage

## Execute Storage
Based on decision:
- Call appropriate MCP tool
- Apply service-specific metadata
- Generate access link

## Provide Context to User
Explain why that storage was chosen
```

**关键技术：**

- 清晰的决策标准
- 备选方案
- 对选择保持透明

### 模式 5：领域特定智能

**使用时机**：你的 Skill 在工具访问之外添加了专业知识。

**示例：金融合规**

```markdown
# Payment Processing with Compliance

## Before Processing (Compliance Check)
1. Fetch transaction details via MCP
2. Apply compliance rules:
   - Check sanctions lists
   - Verify jurisdiction allowances
   - Assess risk level
3. Document compliance decision

## Processing
IF compliance passed:
  - Call payment processing MCP tool
  - Apply appropriate fraud checks
  - Process transaction
ELSE:
  - Flag for review
  - Create compliance case

## Audit Trail
- Log all compliance checks
- Record processing decisions
- Generate audit report
```

**关键技术：**

- 将领域专业知识内嵌到逻辑中
- 操作前先合规检查
- 全面记录
- 明确治理方式

### 故障排查

### Skill 无法上传

#### 错误：“Could not find SKILL.md in uploaded folder”

**原因**：文件没有精确命名为 SKILL.md。

**解决方案：**

- 重命名为 SKILL.md，区分大小写
- 使用以下命令验证，应该能看到 SKILL.md：

```bash
ls -la
```

#### 错误：“Invalid frontmatter”

**原因**：YAML 格式问题。

**常见错误：**

```yaml
# Wrong - missing delimiters
name: my-skill
description: Does things

# Wrong - unclosed quotes
name: my-skill
description: "Does things

# Correct
---
name: my-skill
description: Does things
---
```

#### 错误：“Invalid skill name”

**原因**：名称中有空格或大写字母。

```yaml
# Wrong
name: My Cool Skill

# Correct
name: my-cool-skill
```

### Skill 没有触发

**症状**：Skill 从未自动加载。

**修复**：修改 description 字段。参见“description 字段”中的好坏示例。

**快速检查清单：**

- 它是否过于泛泛？例如 “Helps with projects” 不会有效
- 是否包含用户实际会说的触发短语？
- 如果适用，是否提到了相关文件类型？

**调试方法：**

问 Claude：“When would you use the [skill name] skill?” Claude 会复述 description。根据缺失内容进行调整。

### Skill 过于频繁触发

**症状**：Skill 针对无关查询加载。

**解决方案 1：添加负面触发条件**

```yaml
description: Advanced data analysis for CSV files. Use for statistical modeling, regression, clustering. Do NOT use for simple data exploration (use data-viz skill instead).
```

### 解决方案 2：写得更具体

```yaml
# Too broad
description: Processes documents

# More specific
description: Processes PDF legal documents for contract review
```

### 解决方案 3：澄清范围

```yaml
description: PayFlow payment processing for e-commerce. Use specifically for online payment workflows, not for general financial queries.
```

### MCP 连接问题

**症状**：Skill 加载了，但 MCP 调用失败。

**检查清单：**

1. 验证 MCP server 已连接
   - Claude.ai：Settings > Extensions > [Your Service]
   - 应显示 “Connected” 状态
2. 检查认证
   - API key 有效且未过期
   - 已授予合适的权限或 scopes
   - OAuth token 已刷新
3. 独立测试 MCP
   - 要求 Claude 直接调用 MCP，不使用 Skill
   - “Use [Service] MCP to fetch my projects”
   - 如果失败，问题在 MCP 而非 Skill
4. 验证工具名称
   - Skill 引用了正确的 MCP 工具名称
   - 检查 MCP server 文档
   - 工具名称区分大小写

### 指令未被遵循

**症状**：Skill 加载了，但 Claude 没有遵循指令。

#### 常见原因 1：指令过于冗长

- 保持指令简洁
- 使用项目符号和编号列表
- 把详细参考移动到单独文件

#### 常见原因 2：指令埋得太深

- 把关键指令放在顶部
- 使用 `## Important` 或 `## Critical` 标题
- 必要时重复关键点

#### 常见原因 3：语言模糊

```text
# Bad
Make sure to validate things properly

# Good
CRITICAL: Before calling create_project, verify:
- Project name is non-empty
- At least one team member assigned
- Start date is not in the past
```

高级技巧：对于关键验证，可以考虑打包一个脚本，以编程方式执行检查，而不是依赖语言指令。代码是确定性的，语言解释会有不确定性。Office 相关 Skill 展示了这种模式的示例。

#### 常见原因 4：模型“懒惰”

添加明确鼓励：

```markdown
# Performance Notes

- Take your time to do this thoroughly
- Quality is more important than speed
- Do not skip validation steps
```

注意：把这些内容添加到用户提示中，比添加到 SKILL.md 中更有效。

### 大上下文问题

**症状**：Skill 看起来变慢，或响应质量下降。

### 原因

- Skill 内容过大
- 同时启用了太多 Skill
- 所有内容都被加载，而未使用渐进式披露

### 解决方案

1. **优化 SKILL.md 大小**
   - 把详细文档移动到 references/
   - 链接到 references，而不是内联全部内容
   - 保持 SKILL.md 少于 5,000 词
2. **减少启用的 Skill 数量**
   - 如果同时启用了超过 20 到 50 个 Skill，请评估是否必要
   - 建议选择性启用
   - 考虑为相关能力创建 Skill “包”

## 第 6 章 资源与参考

如果你正在构建第一个 Skill，请从 Best Practices Guide 开始，然后根据需要参考 API 文档。

### 官方文档

#### Anthropic 资源

- Best Practices Guide
- Skills Documentation
- API Reference
- MCP Documentation

#### 博客文章

- Introducing Agent Skills
- Engineering Blog: Equipping Agents for the Real World
- Skills Explained
- How to Create Skills for Claude
- Building Skills for Claude Code
- Improving Frontend Design through Skills

### 示例 Skill

#### 公共 Skill 仓库

- GitHub: anthropics/skills
- 包含 Anthropic 创建、可供你自定义的 Skill

### 工具与实用程序

#### skill-creator Skill

- 内置于 Claude.ai，也可用于 Claude Code
- 可以根据描述生成 Skill
- 会审查并提供建议
- 用法：

```text
"Help me build a skill using skill-creator"
```

#### 验证

- skill-creator 可以评估你的 Skill
- 询问：

```text
"Review this skill and suggest improvements"
```

### 获取支持

#### 技术问题

- 一般问题：Claude Developers Discord 中的社区论坛

#### Bug 报告

- GitHub Issues: anthropics/skills/issues
- 包含：Skill 名称、错误消息、复现步骤

## 参考 A：快速检查清单

使用这份检查清单，在上传前后验证你的 Skill。如果想更快开始，可以使用 skill-creator Skill 生成第一版草稿，然后逐项检查，确保没有遗漏。

### 开始之前

- [ ] 已识别 2 到 3 个具体使用场景
- [ ] 已识别工具，内置工具或 MCP
- [ ] 已阅读本指南和示例 Skill
- [ ] 已规划文件夹结构

### 开发期间

- [ ] 文件夹使用 kebab-case 命名
- [ ] SKILL.md 文件存在，拼写完全正确
- [ ] YAML frontmatter 有 `---` 分隔符
- [ ] name 字段使用 kebab-case，无空格，无大写
- [ ] description 包含做什么和何时使用
- [ ] 不包含任何 XML 标签 `< >`
- [ ] 指令清晰且可执行
- [ ] 包含错误处理
- [ ] 提供示例
- [ ] 清楚链接参考资料

### 上传之前

- [ ] 已测试明显任务上的触发
- [ ] 已测试改述请求上的触发
- [ ] 已验证不会在无关主题上触发
- [ ] 功能测试通过
- [ ] 工具集成可工作，如适用
- [ ] 已压缩为 `.zip` 文件

### 上传之后

- [ ] 在真实对话中测试
- [ ] 监控触发不足或过度触发
- [ ] 收集用户反馈
- [ ] 迭代 description 和指令
- [ ] 更新 metadata 中的版本

## 参考 B：YAML frontmatter

### 必需字段

```yaml
---
name: skill-name-in-kebab-case
description: What it does and when to use it. Include specific trigger phrases.
---
```

### 所有可选字段

```yaml
name: skill-name
description: [required description]
license: MIT # Optional: License for open-source
allowed-tools: "Bash(python:*) Bash(npm:*) WebFetch" # Optional: Restrict tool access
metadata: # Optional: Custom fields
  author: Company Name
  version: 1.0.0
  mcp-server: server-name
  category: productivity
  tags: [project-management, automation]
  documentation: https://example.com/docs
  support: support@example.com
```

### 安全说明

#### 允许

- 任何标准 YAML 类型，例如字符串、数字、布尔值、列表、对象
- 自定义 metadata 字段
- 长 description，最多 1024 个字符

#### 禁止

- XML 尖括号 `< >`，安全限制
- YAML 中执行代码，解析使用安全 YAML
- 名称以 `claude` 或 `anthropic` 为前缀的 Skill，已保留

## 参考 C：完整 Skill 示例

关于展示本指南中模式的完整生产级 Skill，请参考：

- Document Skills：PDF、DOCX、PPTX、XLSX 创建
- Example Skills：各种工作流模式
- Partner Skills Directory：查看来自 Asana、Atlassian、Canva、Figma、Sentry、Zapier 等不同合作伙伴的 Skill

这些仓库会保持更新，并包含本指南未覆盖的其他示例。克隆它们，按你的使用场景修改，并把它们作为模板。


