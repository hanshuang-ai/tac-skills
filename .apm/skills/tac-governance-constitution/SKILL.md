---
name: "tac-governance-constitution"
version: 0.4.5
description: "为项目配置主宪章与专项宪章，建立'1 主宪章 + N 专项宪章'的 AI 编程治理结构"
argument-hint: "项目名称、技术栈和目标环境，如：MyApp Android Kotlin phone"
user-invocable: true
---

## 目标

为当前项目完成宪章配置，而不是只生成单个主宪章文件。

本 Skill 读取内置宪章模版，按项目技术栈和运行环境生成或审校：

1. 主宪章：定义全项目统一的非协商规则、优先级、流程入口和专项宪章登记。
2. 专项宪章：承载具体工作类型的强约束，例如 Android 工程规范、Android Kotlin 编码规范。

生成结果默认落盘到 `.specify/memory/`。项目后续的 `spec.md`、`plan.md`、`tasks.md` 和代码评审必须引用这些宪章。

## 文件资源

### 模版注册表

| 模版 | 输出文件 | 类型 | 适用条件 | 是否默认生成 |
| ---- | -------- | ---- | -------- | ------------ |
| [`templates/constitution.md.tpl`](./templates/constitution.md.tpl) | `.specify/memory/constitution.md` | 主宪章 | 所有项目 | 是 |
| [`templates/input-quality-constitution.md.tpl`](./templates/input-quality-constitution.md.tpl) | `.specify/memory/input-quality-constitution.md` | 输入质量专项宪章 | 所有项目（与技术栈、目标环境无关） | 是 |
| [`templates/android-system-design-constitution.md.tpl`](./templates/android-system-design-constitution.md.tpl) | `.specify/memory/android-system-design-constitution.md` | 工程规范专项宪章 | Android 项目 | Android profile 默认生成 |
| [`templates/kotlin-coding-constitution.md.tpl`](./templates/kotlin-coding-constitution.md.tpl) | `.specify/memory/kotlin-coding-constitution.md` | 编码规范专项宪章 | Kotlin 或 Android/Kotlin 项目 | Android/Kotlin profile 默认生成 |

### 真值规则

- 模版正文是真值来源；生成时不得随意改写、压缩或扩写模版正文。
- 主宪章允许替换 `{{...}}` 占位符；专项宪章模版当前不含占位符，默认原样复制。
- 若新增专项宪章模版，必须先加入“模版注册表”，再更新 profile 选择规则和验证规则。
- 只有注册表中存在模版的专项宪章才由本 Skill 生成；主宪章中登记但尚无模版的专项宪章，只能保留登记入口，不得编造正文。

## 执行模式

默认执行 **configure** 模式。

| 模式 | 触发语义 | 行为 |
| ---- | -------- | ---- |
| `configure` | “配置宪章”“初始化宪章”“生成宪章” | 收集配置，生成主宪章和匹配专项宪章 |
| `audit` | “检查宪章”“审计宪章”“是否合规” | 只检查现有宪章、模版注册和残留占位符，不覆盖文件 |
| `refresh` | “按模板刷新”“重新生成” | 对已存在宪章按当前模版更新；覆盖前必须说明会覆盖哪些文件 |

若用户未指定模式，按 `configure` 执行。

## 执行步骤

### 1. 识别项目配置

先从用户参数、现有 `.specify/memory/constitution.md`、`PROJECT.md`、`README.md`、构建文件和目录结构中提取配置；只有缺失关键信息时才询问用户。

最少需要以下信息：

| 配置项 | 示例 | 用途 | 缺省策略 |
| ------ | ---- | ---- | -------- |
| 项目名称 | `示例 Android 应用` | 主宪章标题 | 从仓库目录名推断，无法确认则询问 |
| 技术栈 | `Android/Kotlin` | profile 与专项宪章选择 | 从 Gradle、AGP、Kotlin 插件推断 |
| 文档语言 | `中文` / `English` | 主宪章原则 II | 默认中文 |
| 目标环境 | `手机` / `车载` / `平板` / `TV` / `无特殊约束` | 主宪章原则 III | 无法确认则用“无特殊约束” |
| 评审流程 | `Gerrit` / `GitHub PR` / `GitLab MR` / `无` | 主宪章研发流程 | 无法确认则用“无” |
| 包名空间 | `com.example.app` | 主宪章技术边界 | Android 从 `namespace` 或 `applicationId` 推断 |
| 输出策略 | `create-only` / `overwrite` / `merge-review` | 写入文件 | 默认 `create-only` |

### 2. 选择 Profile

按技术栈选择 profile。一个 profile 对应一个主宪章和若干专项宪章。

| Profile | 匹配条件 | 生成文件 |
| ------- | -------- | -------- |
| `android-kotlin` | Android + Kotlin | `constitution.md`、`input-quality-constitution.md`、`android-system-design-constitution.md`、`kotlin-coding-constitution.md` |
| `android` | Android 但无法确认 Kotlin | `constitution.md`、`input-quality-constitution.md`、`android-system-design-constitution.md` |
| `kotlin` | 非 Android Kotlin 项目 | `constitution.md`、`input-quality-constitution.md`、`kotlin-coding-constitution.md` |
| `generic` | 未匹配到已支持技术栈 | `constitution.md`、`input-quality-constitution.md` |

> 输入质量专项宪章与具体技术栈、目标环境无关，是 AI 工具接收工作请求的通用前置闸门，因此所有 profile 默认生成；除非用户在 `configure` 阶段显式声明跳过，否则不得省略。

匹配规则：

- 同时存在 Android Gradle Plugin 和 Kotlin Android 插件时，使用 `android-kotlin`。
- 仅存在 Android Gradle Plugin 时，使用 `android`。
- 仅存在 Kotlin JVM 或 Kotlin Multiplatform 且无 Android 插件时，使用 `kotlin`。
- 其他情况使用 `generic`，不得强行套用 Android 或 Kotlin 专项宪章。

### 3. 生成主宪章

读取 `templates/constitution.md.tpl`，替换所有占位符后写入 `.specify/memory/constitution.md`。

#### 主宪章占位符规则

| 占位符 | 取值规则 |
| ------ | -------- |
| `{{项目名称}}` | 用户输入或仓库名 |
| `{{文档语言}}` | `中文` 或 `English` |
| `{{对侧语言}}` | 文档语言为中文时填 `英文`；为 English 时填 `Chinese` |
| `{{场景}}` | 目标环境，例如 `手机`、`车载`、`平板`、`TV`、`无特殊约束` |
| `{{场景约束描述}}` | 根据目标环境生成整段约束文本，见下方“目标环境约束文本” |
| `{{技术栈}}` | `Android`、`Android/Kotlin`、`Kotlin` 或其他技术栈描述 |
| `{{源码语言}}` | `Kotlin`、`Java`、`Swift`、`TypeScript`、`Go` 等 |
| `{{构建脚本类型}}` | Android/Kotlin: `Gradle 脚本`；其他技术栈按实际构建系统填写 |
| `{{平台敏感面}}` | Android: `UI、资源、清单、权限或设备行为`；其他技术栈按平台填写 |
| `{{对应集成/仪器测试}}` | Android: `仪器测试或 UI 测试`；其他技术栈按测试体系填写 |
| `{{构建命令}}` | Android 默认 `assembleDebug`；无法确认时写项目实际构建命令 |
| `{{单元测试命令}}` | Android 默认 `testDebugUnitTest`；无法确认时写项目实际测试命令 |
| `{{静态检查命令}}` | Android 默认 `lintDebug`；无法确认时写项目实际静态检查命令 |
| `{{工程规范文件名}}` | Android: `android-system-design-constitution.md`；其他技术栈按 profile 填写 |
| `{{编码规范文件名}}` | Kotlin: `kotlin-coding-constitution.md`；其他语言按 profile 填写 |
| `{{包名空间}}` | Android `namespace` / `applicationId`，或用户输入 |
| `{{评审流程描述}}` | 根据评审流程生成整段文本 |

#### 目标环境约束文本

- **手机**：
  `所有功能设计必须优先满足手机端使用约束，包括多屏适配、网络切换、电量优化、权限最小化、冷启动性能和后台限制。涉及后台行为、推送、定位、相机、存储等敏感能力时，必须显式评估隐私、权限和合规影响。理由：目标运行环境为消费级移动端，需要在多样化设备、系统版本和网络条件下稳定运行。`
- **车载**：
  `所有功能设计必须优先满足车载端使用约束，包括驾驶中可理解性、弱网或离线容错、受限输入方式、稳定启动与资源占用可控。涉及交互、通知、权限、后台行为或外设能力时，必须显式评估对车载安全体验、兼容性和恢复路径的影响。理由：目标运行环境为车载设备，研发产物必须适配真实车载环境而非默认套用手机场景。`
- **平板 / 折叠屏**：
  `所有功能设计必须优先满足大屏、多窗口、横竖屏切换、状态恢复和输入方式差异。涉及布局、导航、列表、弹窗和媒体展示时，必须显式评估响应式布局、可访问性和恢复路径。理由：目标运行环境存在屏幕形态变化，不能把手机单栏假设作为默认设计。`
- **TV / Wear OS / XR / 嵌入式 Android**：
  `所有功能设计必须显式识别目标设备的输入方式、显示约束、系统限制、后台策略、性能资源和恢复路径。涉及平台能力或系统服务时，必须说明适配边界和降级方案。理由：特殊 Android 设备形态与手机存在显著差异，必须用项目级设计约束承接。`
- **无特殊约束**：
  `所有功能设计必须显式列出目标运行环境的关键约束，并据此评估交互、可用性、性能与兼容性。理由：缺省场景下也必须先识别约束，否则容易把通用假设错配给特定环境。`

#### 评审流程文本

- **Gerrit**：`提交必须遵循 Change-Id 规则，强制 +2 后提交；评审时必须检查宪章符合性、TDD 顺序与专项宪章引用。`
- **GitHub PR**：`PR 必须使用模板，至少一名 reviewer 通过并附宪章符合性检查清单；禁止直接 push 至主分支。`
- **GitLab MR**：`MR 必须使用模板，至少一名 maintainer Approve 并附宪章符合性检查清单；禁止直接 push 至主分支。`
- **无**：`仍要求本地走 Spec Kit 三件套（spec/plan/tasks）与质量闸门，禁止裸提主分支。`

### 4. 生成专项宪章

按 profile 复制对应专项宪章模版到 `.specify/memory/`：

- 所有 profile（含 `generic`）：复制输入质量专项宪章 `input-quality-constitution.md`。
- `android-kotlin`：另复制 Android 工程规范专项宪章和 Kotlin 编码规范专项宪章。
- `android`：另复制 Android 工程规范专项宪章。
- `kotlin`：另复制 Kotlin 编码规范专项宪章。
- `generic`：除输入质量专项宪章外，不生成其他专项宪章，除非用户明确指定已有模版。

专项宪章写入规则：

- 当前专项宪章模版无占位符，默认原样复制。
- 如果目标文件已存在且输出策略是 `create-only`，不得覆盖；输出待处理清单。
- 如果目标文件已存在且输出策略是 `merge-review`，必须先比较差异，再提示用户人工确认。
- 如果目标文件已存在且输出策略是 `overwrite`，覆盖前必须列出文件路径和风险。

### 5. 同步主宪章登记

主宪章的“专项规范清单”必须与本次生成结果一致：

- 所有 profile 生成了 `input-quality-constitution.md`，主宪章必须登记输入质量专项宪章；该条目是 AI 工具接收功能开发 / Bug 修复请求时的输入完整性闸门，不得省略。
- profile 生成了 `android-system-design-constitution.md`，主宪章必须登记工程规范专项宪章。
- profile 生成了 `kotlin-coding-constitution.md`，主宪章必须登记编码规范专项宪章。
- 主宪章模版中登记了 `document-governance-constitution.md`，但本 Skill 当前没有对应模版；生成后必须在交付说明中标记为“已登记、待生成”。
- 不得登记不存在且无生成计划的专项宪章，除非主宪章模版明确保留该入口。

### 6. 验证

生成或审校后必须执行以下检查：

- `.specify/memory/constitution.md` 存在。
- 主宪章包含 11 个核心原则，编号为 I–XI。
- `.specify/memory/input-quality-constitution.md` 存在；该文件是所有 profile 的必备产物。
- 已选 profile 对应的其他专项宪章文件存在，或在交付说明中列为未生成原因。
- 全部生成文件中 `{{` 和 `}}` 为 0 命中。
- 主宪章登记的工程规范、编码规范、输入质量专项宪章文件名与实际输出文件一致。
- 输入质量专项宪章不得包含具体项目、业务、单一工具的 Hook 脚本名或固定项目路径；与项目接入相关的细节应由 `PROJECT.md` 或运行说明承载。
- Android 工程规范专项宪章不得包含具体项目、业务、单一设备形态或固定项目路径。
- Android Kotlin 编码规范专项宪章必须保留 Google Android Kotlin Style Guide 与 Kotlin 官方编码规范来源链接。
- 若目标文件已存在但未覆盖，必须列出跳过原因。

### 7. 交付说明

完成后向用户说明：

- 使用的 profile。
- 生成、跳过、待人工处理的文件列表。
- 是否存在未生成但已登记的专项宪章。
- 是否存在残留占位符。
- 下一步建议：运行 `/tac-governance-project` 生成 `PROJECT.md`，并按项目需要继续补充文档治理、研发流程或功能点分析专项宪章。

## 设计原则

- **配置优先**：本 Skill 的职责是把项目接入“1 主宪章 + N 专项宪章”治理结构，而不是只产出单个 Markdown。
- **注册表驱动**：所有可生成宪章必须先在模版注册表中声明，避免隐藏产物和不可追溯的生成逻辑。
- **Profile 收敛**：项目只需要选择技术栈 profile；profile 决定默认生成哪些专项宪章。
- **不编造专项**：没有模版的专项宪章不得由 AI 即兴生成正文，只能登记为待补充或交由对应 Skill 生成。
- **幂等写入**：默认不覆盖已有宪章；覆盖必须显式说明影响。
- **来源可追溯**：专项宪章必须保留权威来源、适用边界和与主宪章的优先级关系。
