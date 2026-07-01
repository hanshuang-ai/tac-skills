---
name: "tac-maestro-case"
version: 0.4.5
description: >
  LLM-A Case Writer: 读取需求/设计/代码资料，生成可追溯的 Maestro 测试用例(.case.md)和
  Maestro flow(.yaml)，输出覆盖矩阵和后续 Review Gate 交接信息。
  触发：用户说'生成Maestro用例''写E2E测试''生成flow''生成测试用例''自动化用例'
  '覆盖quickstart''覆盖验收路径'等。所在环节：测试用例生成。
---

# Maestro Case Writer Skill

本 Skill 实现 LLM-A 角色：读取项目资料，产出结构化测试用例和 Maestro flow。

## 硬性约束

1. 本 Skill **不执行设备测试**，不连接 Maestro MCP，不使用 `inspect_screen`。
2. 不能根据屏幕现象擅自修改需求预期。
3. 产出的 `.case.md` 必须包含全部 13 个标准字段（见 Step 3）。
4. 每条断言必须能追溯到一个资料来源（quickstart 路径、AC 编号、FR 编号或页面规则）。
5. Execution Record 留空，由 `tac-maestro-run` Skill 填写。
6. 本 Skill 完成产物生成后即停止，不执行主 agent 自检，不主动启动 subagent；Review Gate、subagent 静态验证和设备执行均作为后续流程处理。
7. 生成 flow 时不得默认依赖某个具体 seed 名称、分类名、商品名、应用名、订单名或搜索结果名；只有需求明确要求验证该具体数据，且 Preconditions 能提供确定 setup 时，才允许使用固定业务文案。

## Step 1: 收集并确认资料路径（不可跳过）

检查用户输入是否提供以下信息。**Feature 名称 + 至少一个资料来源必须齐全才能进入 Step 2。**

| 字段 | 必填 | 说明 |
|------|------|------|
| Feature 名称 | 是 | 与 `specs/<feature>/` 目录对应 |
| quickstart 路径 | 是（推荐） | `specs/<feature>/quickstart.md`，首选资料来源 |
| spec 路径 | 否 | `specs/<feature>/spec.md`，补充 FR/AC |
| 页面摘要/设计映射 | 否 | `persistent-assets/design/_baseline/ui/*.md`、`persistent-assets/design/_baseline/0[1-3]-*.md` |
| 已有同类 flow | 否 | 参考选择器和结构风格 |
| 关键代码入口 | 否 | Activity、布局 XML、ViewModel 等 |

**追问模板（缺失 Feature 名称或资料路径时使用）：**

> 为了生成可追溯的 Maestro 测试用例，请补充以下信息：
>
> 1. Feature 名称（对应 specs 目录名）？
> 2. quickstart/spec 路径？
> 3. 是否有已有 Maestro flow 可参考？

## Step 2: 读取资料并分析测试路径

1. 读取 Step 1 确认的所有资料文件。
2. 提取所有可验证路径（quickstart 中的 Path A/B/C...、spec 中的 AC/FR）。
3. 对每条路径判断 Maestro 自动化可行性：
   - 可自动化：标记为待生成。
   - 不可自动化：记录原因（如需要物理操作、需要外部服务状态等）。
4. 如果用户提供了关键代码入口，提取页面上的 `android:id` 清单用于后续选择器选择。
5. 提取可见文案时必须记录精确来源：优先记录生成该文案的代码、布局或 `strings.xml` 资源；如果文案来自状态绑定、adapter、resolver 或 ViewModel，不得只笼统引用 `strings.xml` 或页面名称。
6. 判断测试路径是否真正需要固定业务数据：
   - 若目标是验证页面结构、列表存在、卡片可点击、详情页可打开、分类可切换、按钮状态变化，应优先写成数据无关用例。
   - 若目标是验证某条特定 seed、某个指定名称或某类固定结果，必须在 Preconditions 中写明 setup 来源和准备方式；无法稳定准备时，将该路径标记为"需 Setup"或"不可稳定自动化"。
   - 不得把"当前代码里刚好存在的样例数据"当作稳定验收条件，除非 spec/quickstart 明确要求该样例数据本身。

## Step 3: 生成 .case.md 和 .yaml

对每条待生成路径：

### 3.1 生成 `.case.md`

路径：`persistent-assets/automated-testing/_baseline/cases/<feature>/<case_id>.case.md`

使用本 Skill 内置模板 `templates/test-case.template.md`，确保包含以下 13 个字段：

1. Case ID
2. Title
3. Feature
4. Source Materials（必须有具体文件路径和章节）
5. Traceability（每条断言 → 需求映射）
6. Preconditions
7. Test Data
8. Device Requirements
9. Steps（清晰编号的操作步骤）
10. Expected Results（与 Steps 一一对应）
11. Maestro Flow（指向 .yaml 的路径 + 脚本参数）
12. Reset Strategy（前置清理和后置恢复命令）
13. Known Risks（选择器风险 + 缓解策略）

### 3.2 生成 `.yaml`

路径：`persistent-assets/automated-testing/_baseline/flows/<case_id>.yaml`

YAML 规则：

- 必须包含 `appId`、`name`、`tags`、`properties.sourceSpec`、`properties.path`。
- 选择器优先级：`id` > `contentDescription` > `text` > `position`。
- 每个选择器标注稳定性等级：

| 等级 | 选择器类型 | 风险 |
|------|-----------|------|
| S1 | `android:id` / `com.xxx:id/xxx` | 低 |
| S2 | `contentDescription` | 低-中 |
| S3 | 精确文本匹配（中文） | 中 |
| S4 | 模糊文本 / 位置关系 | 高 |

- S3/S4 级选择器必须在 `.case.md` 的 Known Risks 中记录。
- 正则文本、包含 `.*` / `|` / 部分匹配语义的文本选择器一律按 S4 处理，即使匹配的是精确枚举文案。
- `below` / `above` / `leftOf` / `rightOf`、`index`、坐标、滚动后点击、多候选同文案点击一律按 S4 处理。
- `.case.md` 的 Test Data / Source Materials 必须引用到选择器或断言的真实来源文件；文案来自代码状态绑定时，应引用具体状态绑定代码文件，而不是只引用资源文件或宽泛模块说明。
- 超过 3 秒的等待必须使用 `extendedWaitUntil` 并标注 timeout。
- 禁止自行"推测"控件 id，只能从代码/布局文件中提取或标记为"需 MCP 现场修正"。

数据无关 flow 规则：

- 列表结构类用例：不要断言某个固定 item 文案；应断言列表容器 id、首个可见 item 的稳定子控件 id、关键按钮 id。
- 列表点击进入详情类用例：不要点击固定 item 名称；可点击首个可见 item 的稳定名称控件或卡片主体，并用目标页稳定标题、容器 id、主按钮 id 或状态正则确认跳转成功。
- 切换/筛选类用例：不要固定断言切换后的具体结果名称；可用 `copyTextFrom` 记录切换前后的可见 item 文案，再用 `assertTrue` 校验内容发生变化，同时保留列表容器 id 断言。
- 状态动作类用例：若动作只对某种状态有效，先选择当前可见的目标状态控件（如"下载"、"待处理"、"可提交"），不要默认点击第一个 item；若只能靠 `index` 关联同一卡片内名称和按钮，必须在 Known Risks 中标注这是 S4 风险，交给 `tac-maestro-run` 现场校准。
- 详情页内容类用例：如无法动态保存并复核所选 item 名称，不要断言固定业务名称；优先断言详情页稳定结构、标题、主按钮、状态变化和可交互结果。
- 当必须使用固定文案时，`.case.md` 的 Preconditions 必须说明该数据如何通过 mock、seed、脚本参数或外部命令稳定准备；否则不生成依赖该固定文案的 PASS/FAIL 自动化断言。

## Step 4: 生成覆盖矩阵

在 `persistent-assets/automated-testing/_baseline/cases/<feature>/coverage-matrix.md` 中输出：

```markdown
# <Feature> Maestro 覆盖矩阵

| 需求来源 | 路径/AC | Case ID | Flow | 状态 | 未覆盖原因 |
|----------|---------|---------|------|------|-----------|
| quickstart.md | Path A | xxx | xxx.yaml | 已生成 | — |
| quickstart.md | Path B | — | — | 未覆盖 | 需要外部服务 mock |
```

## Step 5: 停止并交接后续验证

产物生成完成后立即停止本 Skill 流程，并向用户交接后续 Review Gate 输入。不得在本 Step 中执行主 agent 自检、不得主动调用 Maestro、不得主动启动 subagent。

交接信息必须包含以下验证清单，供后续 subagent 静态验证或 `tac-maestro-run` 使用：

- 每条 `.yaml` 需要通过 Maestro 语法解析。
- 每条用例至少有一个明确资料来源。
- 每条 flow 需要包含 `name`、`tags`、`properties.sourceSpec`、`properties.path`。
- S3/S4 级选择器需要有替代策略或风险标注；正则文本选择器必须按 S4 审查。
- 固定业务数据文案需要有明确 setup；没有 setup 的列表、分类、详情、状态动作 flow 应优先采用数据无关断言。
- 不应存在未填写的占位符（`<xxx>` 形式）、TODO 或 FIXME。
- 前置条件应能通过脚本参数或明确的外部命令准备（ClearAppData、UninstallPackage、StartActivity 等）。
- Execution Record 必须留空。

如用户后续明确要求 subagent 静态验证，subagent 审查范围仅限字段完整性、断言可追溯性、flow 必填属性、选择器风险标注、占位符残留、Execution Record 留空和覆盖矩阵合理性。

## Step 6: 输出总结

最终向用户报告：

1. 读取的资料列表
2. 生成的用例和 flow 清单
3. 覆盖矩阵摘要（已覆盖/未覆盖数量）
4. 已知风险清单
5. 后续 Review Gate 交接状态：
   - `Review Gate: 待后续 subagent 静态验证`
   - `Review Gate: 待 tac-maestro-run 执行验证`
6. 推荐的 `tac-maestro-run` 执行命令模板

## 参考文件

| 文件 | 用途 |
|------|------|
| `templates/test-case.template.md` | 用例模板 |
| `prompts/case-writer.prompt.md` | 用例生成 prompt |
| `references/selector-stability.md` | 选择器稳定性评级指南 |
| `references/coverage-matrix-guide.md` | 覆盖矩阵编写规范 |
| `references/workflow-boundary.md` | Case Writer / Execution Validator 职责边界 |
