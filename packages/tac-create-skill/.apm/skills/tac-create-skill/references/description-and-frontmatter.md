# frontmatter 与 description 写作规则

YAML frontmatter 是 Agent 系统提示的一部分，是「这个 skill 该不该加载」的唯一判据。这里写不对，正文再好也救不回来。

## 字段总览

| 字段 | 必填 | 规则 |
|---|---|---|
| `name` | 是 | kebab-case；与目录名一致；禁含 `claude` / `anthropic`（保留名）；不允许空格 / 下划线 / 大写 |
| `description` | 是 | ≤1024 字符；禁 `<` / `>`（避免注入系统提示）；必含「做什么 + 何时用 + 触发短语」三段 |
| `user-invocable` | 否 | `true` 启用 `/<name>` 显式调用；**强烈推荐 `true`**——自动调度可重复性弱，显式调用更稳 |
| `license` | 否 | 开源时填，常见 `MIT` / `Apache-2.0` |
| `compatibility` | 否 | 1-500 字符；标注目标产品 / 系统包 / 网络等环境约束 |
| `metadata` | 否 | 任意 key/value；推荐 `author` / `version` / `mcp-server` / `category` / `tags` |
| `allowed-tools` | 否 | 限制 skill 可用工具，格式如 `"Bash(python:*) Bash(npm:*) WebFetch"` |

> **关于 `version`**：是否纳入 frontmatter、按什么节奏 bump，取决于消费场景的约定（如包管理 / CI 治理）。本写作规则不强制具体节奏，但**一旦填了就要保持与发布渠道一致**。

## 命名 kebab-case 对比

```yaml
# ✅ 正确
name: my-cool-skill
name: tac-create-skill
name: ux-handoff

# ❌ 错误
name: My Cool Skill           # 含空格、大写
name: my_cool_skill           # 下划线
name: MyCoolSkill             # PascalCase
name: claude-helper           # 名中含 claude（保留）
```

## description 三段式公式

```text
[做什么] + [当用户说"短语1"/"短语2"/"短语3"时触发] + [产物 / 落点 / 边界]
```

三段缺一会导致以下问题：

| 缺哪段 | 后果 |
|---|---|
| 缺「做什么」 | 模型不知道何时该用 |
| 缺「触发短语」 | 永远不会被自动加载，只能 `/<name>` 显式调用 |
| 缺「产物 / 落点 / 边界」 | 触发过度，混入相邻场景 |

## 好坏对比

### ✅ 好的 description

```yaml
# 具体动词 + 文件类型 + 触发短语
description: "分析 Figma 设计稿并生成开发交付文档。当用户上传 .fig 文件、或说'设计规范'/'组件文档'/'设计稿落地'时触发；产物落 design-handoff/ 目录。"

# 含负面触发，避免过度抢
description: "测试用例规划（不连设备）。当用户说'写自测用例'/'生成 case'/'测试规划'时触发；只写文档不跑设备，设备执行交由对应执行 skill。"

# 工作流入口，触发场景多元
description: "Feature 开发入口，强制按需求模板收集结构化输入。触发：用户说'新增'/'添加'/'实现'/'开发'/'创建'/'修改行为'/'重构'/'优化'等；**不**包含'修复'/'缺陷'类（走 BugFix 入口）。"
```

### ❌ 差的 description

```yaml
# 太泛
description: "Helps with projects."
description: "处理文档。"

# 缺触发短语
description: "Creates sophisticated multi-page documentation systems."

# 过于技术，不是用户的话
description: "Implements the Project entity model with hierarchical relationships."

# 长但全是废话
description: "这是一个强大的工具，可以帮助你完成各种任务，使用方便，效果出色。"
```

## 触发短语怎么收集

**不要造词**。回去问业务：

- 用户上次手动做这件事时说了什么？把那句原话记下来。
- 团队里高频说法是哪几个？同义词 / 缩写 / 中英混用都收。
- 故意收一些「看起来像但其实不是」的近邻短语 → 用「不要用于 X」收窄。

### 收集模板

| 场景类别 | 用户原话示例 | 收为触发短语 |
|---|---|---|
| 新功能开发 | "帮我做个登录页" / "新增分享功能" | 新增 / 添加 / 做个 / 实现 |
| Bug 修复 | "修一下崩溃" / "解决卡顿问题" | 修复 / 解决 / 修一下 / bug |
| 评审入口 | "帮我 review 下" / "评审 PR" | review / 评审 / 检查代码 |
| 文档生成 | "写一份 spec" / "出技术方案" | spec / 技术方案 / 设计文档 |

## 触发不足 vs 触发过度的调优

### 触发不足（症状：应该用却没自动加载）

**原因**：description 太泛、缺关键词、缺用户原话。

**修法**：

- 加细分关键词（尤其技术术语 / 文件类型 / 工具名）
- 加多种说法（"feature" + "功能" + "需求"）
- 在 description 里复述场景细节（用户的 job context、文件路径线索）
- 末尾加 push 短语：「**Always use this skill whenever the user mentions ...**」

### 触发过度（症状：无关查询也加载）

**原因**：description 太宽、与相邻 skill 重叠。

**修法**：

- 加负面触发：「Do NOT use for X (use other-skill instead)」
- 收窄范围（指明文件类型 / 工作环节 / 业务领域）
- 把场景钉死到具体工作流，避免「helps with X」类泛词

## 安全限制

frontmatter 会出现在 Agent 的系统提示中。**禁止**：

- XML 尖括号 `<` / `>`（潜在注入 vector）
- 名称以 `claude` 或 `anthropic` 为前缀（保留名）
- YAML 中执行代码（用安全 YAML 解析）

## YAML 最小可用模板

```yaml
---
name: "your-skill-name"
description: "做什么。当用户说 X / Y / Z 时触发；产物落点。"
user-invocable: true
metadata:
  author: your-name
---
```

复制这个 → 替换 3 个占位符 → 自检通过即可。
