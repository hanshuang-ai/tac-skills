---
name: tac-requirement-decomposition
description: >
  需求拆分工程化 SKILL（v4.5）。将已验证业务需求按"模块→功能组"二级粒度拆分为 Story，
  每个功能组即为一个独立的 Story，以功能组为最小拆分单位，不再向下细分。
  拆分粒度示例：首页 → Banner、应用推荐、应用分类（各为一个 Story）。
  每个 Story 输出九字段（功能/场景/输入/输出/约束/验收标准/迭代标识/日期/参考）。
  参考字段结构化溯源：需求文档章节级引用 + UI/UE 文档章节级映射 + 所有设计输入文档完整追溯。
  通过迭代标识区分需求批次，避免不同日期拆同一份需求产生重复。
  每个字段均标明来源于哪个设计文档的哪个章节（PRD/业务领域/HLD/DLD/交互稿/UI稿/验收标准/自测用例）。
  适配 0-1（从零构建）、1-N（增量迭代）、Bugfix（缺陷修复）三种场景。
  严禁使用批量脚本/模板生成 Story——每个 Story 必须从设计文档中单独提取内容。
  v4.5 新增质量保障三层防线：RTM 锚点防偏离 + AC 独立验证防遗漏 + DLD 接口绑定防不可实施。
  Use when user mentions: 拆分需求, 需求分解, 需求拆解, requirement decomposition,
  story拆分, 功能拆分, 拆story, 拆分story, 任务拆分, 写story, 需求分析,
  decompose requirement, break down requirements.
version: 0.4.5
user-invocable: true
metadata:
  author: TAC Team
  category: requirement-engineering
  tags: [requirement, decomposition, story, speckit, specify, 需求拆分, 功能组, 迭代标识, 完整溯源, 逐Story生成, 质量保障, RTM, 覆盖验证]
---

# 拆分需求 SKILL

## 一句话定义

将"已验证的业务需求"按 **模块 → 功能组** 拆分，**每个功能组即为一个 Story（最小拆分单位，不再向下细分）**，输出 **九字段** 完整描述，投递给 Speckit/Specify 进入工程实现。

> **迭代标识 vs 日期**：`迭代标识`绑定需求文档版本（SRS），区分一期/二期；`日期`仅记录拆分执行时间。同份需求在不同日期拆分时迭代标识不变，日期会变——这确保不会因为重复执行而误判为两个独立的批次。

### 拆分粒度规则

> **以功能组级为准，不再向下拆分。**

| 模块 | 功能组（= Story） |
|------|------------------|
| 首页 | Banner、应用推荐、应用分类 |
| 详情页 | 基础信息展示、评论区、相关推荐 |
| 下载管理 | 下载列表、下载进度、安装管理 |
| 个人中心 | 用户信息、我的收藏、系统设置 |

---

## 适用场景判断

开始前先判定场景类型：

| 用户信号 | 场景 | 策略要点 |
|----------|:----:|----------|
| "新项目""从零开发""全新模块" | **0-1** | 全量构建功能树，约束必含技术栈 |
| "新增""迭代""二期""增强" | **1-N** | 只拆增量，标注兼容性 |
| "修复""bug""crash""报错" | **Bugfix** | 1 Bug≈1 Story，场景含复现路径 |

> 详细场景策略见 `references/scenario-guide.md`

---

## 输入要求

| # | 输入 | 0-1 | 1-N | Bugfix |
|---|------|:---:|:---:|:------:|
| 1 | 需求设计产物（冻结版） | ✅ | ✅ | ✅ |
| 2 | 业务领域设计 | ✅ | ✅ | 可选 |
| 3 | 概设 (HLD) | ✅ | ✅ | 可选 |
| 4 | 详设 (DLD) | ✅ | ✅(增量) | 可选 |
| 5 | 验收标准 (AC) | ✅ | ✅ | ✅ |
| 6 | 需求验证结论 | ✅ | ✅ | ✅ |
| 7 | 交互&视觉验收稿 | ✅ | ✅(增量) | 条件 |

**缺失任一项且不允许推断 → 拒绝执行，输出缺失清单。**

---

## 质量保障三层防线（v4.5 新增）

> AI 每次拆分的输出天然不完全一致——结构漂移（Story 分组边界不同）、内容漂移（详略程度不同）、遗漏漂移（某些功能组被忽略）。
> 解决方案不是"让 AI 输出一模一样"，而是**用外部锚点约束它**。

### 防线 1：RTM 固定锚点（防偏离）

**核心原理**: 在 AI 拆分之前，先建立一份**人工确认的需求可追溯矩阵（RTM）**作为"正确答案"。RTM 由以下不可变参照点组成：

| 参照源 | 数量 | 说明 |
|--------|:---:|------|
| PRD §3.1 In-Scope 条目 | 21 条（视具体项目） | 每个条目必须被**恰好一个** Story 作为主要承载方 |
| 业务规则 R1-R34 | 约 30-50 条 | 每条规则必须出现在至少一个 Story 的"约束"字段 |
| 验收用例全集 (AC) | 视项目规模 | 166 条 AC 必须全部出现在至少一个 Story 的 `acceptance_criteria.items` |

**RTM 必须是拆分前人工确认的，不是 AI 产出的。**
AI 拆分完成后，对照 RTM 逐行验证：哪个条目没 Story？哪个 Story 没有归属？

**输出文件**: `persistent-assets/spec-tasks/requirements-traceability-matrix.md`

### 防线 2：AC 独立验证（防遗漏）

**核心原理**: 验收用例（AC）是独立于拆分流程的第三方参照——它不是 AI 产物，而是设计文档的一部分。166 条 AC 全集必须全部在 Story 中出现。

**验证方法**: 遍历所有 Story 的 `acceptance_criteria.items`，提取 AC 编号（如 `AC-HOM-FN-01`），与 AC 全集做集合求差：
- 未出现的 AC → 遗漏告警
- 出现在多个 Story 中的 AC → 粒度冲突告警
- 引用了不存在 AC 编号的 → 幻觉告警

### 防线 3：DLD 接口绑定（防不可实施）

**核心原理**: Story 的 `input` 和 `output` 字段必须精确到 DLD 接口级别，开发人员拿到后不需要回翻 DLD 才能找到具体接口名和参数类型。

**强制要求**:
- `input.source` 必须包含 DLD §章节号 + 接口名 + 参数类型（如 `DLD §4.7.3 接口1 fetchAppList(category: String?): Result<AppListDto>`）
- `output.result` 必须包含响应类型（如 `StateFlow<UiState>(Loading/Cached/Loaded/Empty/Error)`）
- 禁止模糊写法："从平台API获取"、"展示应用列表"

### 多次拆分一致性策略

当需要对同一份需求进行多次拆分时（如设计文档微调后重新拆分），**把上次产出的 `decomposition_index.yaml` 作为本次拆分的输入锚点**：

```
约束规则：保持模块边界和 Story 粒度与上次一致。仅当设计文档有新增/修订内容时才调整。
若设计文档未变，输出必须与上次一致。
```

这样每一次运行都在"上次的骨架"上微调，而不是从零重建。

> 完整策略文档见 `references/quality-assurance-strategy.md`

---

## 拆分执行步骤

### Step 0：准备质量锚点（v4.5 新增）

在开始拆分前，先人工确认以下信息，写入 `requirements-traceability-matrix.md`：

1. **提取所有 In-Scope 条目**：从 PRD §3.1（或等效章节）列出所有必须在本次交付的功能项，每个条目一行
2. **列出全部业务规则**：从领域设计 §8（或等效章节）列出所有 R# 编号
3. **整理 AC 用例全集**：从验收标准文档提取全部用例编号清单
4. **读取上次拆分结果**（如有）：读 `decomposition_index.yaml` 作为模块边界的参照锚点

> 这些是"正确答案"——AI 拆分完成后逐一对照，缺失即为不合格。

### Step 1：场景判定
按上表判定 0-1 / 1-N / Bugfix。

### Step 2：识别功能组
从 PRD 信息架构识别 **模块 → 功能组**：
- **一个功能组 = 一个 Story，不再向下细分**
- 禁止跨模块混合
- 禁止以技术组件为拆分起点
- 拆分粒度示例：首页 → `Banner`、`应用推荐`、`应用分类`（各为一个独立 Story）
- **确定迭代标识**：0-1 场景设为 `IT-V1.0`（绑定 SRS 版本号）；1-N 场景读取既有索引中最大迭代标识后递增（如 `IT-V1.1`）

### Step 3：为每个 Story 填充九字段

| # | 字段 | 必填 | 说明 | 来源（需在参考表中标注到§章节） |
|---|------|:---:|------|------|
| 1 | **功能** | ✅ | 一句话描述功能目标 | PRD §章节 |
| 2 | **场景** | ✅ | 从哪里进入→做什么→看到什么 | PRD §章节 + 交互稿 §规则 |
| 3 | **输入** | ✅ | 接收什么数据 + 数据来源（**v4.5: 必须精确到 DLD 接口名+参数类型**） | 详设(DLD) §接口 |
| 4 | **输出** | ✅ | 产出什么结果 + 如何展示（**v4.5: 必须含响应类型/数据结构**） | 交互稿 §规则 + 详设 §响应 |
| 5 | **约束** | ✅ | 技术栈/性能/兼容/安全/车机（**v4.5: 至少 1 条含量化指标**） | HLD §架构 + 非功能需求 |
| 6 | **验收标准** | ✅ | 五选一验证方式 | AC 用例编号 + 自测用例编号 |
| 7 | **迭代标识** | ✅ | 需求批次 ID（如 `IT-V1.0`），绑定 SRS 版本 | 需求版本号 |
| 8 | **日期** | ✅ | 拆分执行日期 YYYY-MM-DD | 拆分当日 |
| 9 | **参考** | ✅ | 结构化溯源表（见下方映射规则） | 全部设计文档 |

> **v4.5 实施就绪要求**：
> - `input.source` 必须包含 DLD §章节号 + 接口名 + 参数类型，示例：`DLD §4.7.3 接口1 fetchAppList(category: String?): Result<AppListDto>`
> - `output.result` 必须包含响应类型/数据结构，示例：`StateFlow<UiState>(Loading/Cached/Loaded/Empty/Error)`
> - `constraints` 至少 1 条含量化指标，示例：`冷启动 95%分位 ≤3000ms (HLD §11 NFR)`
> - `acceptance_criteria.items` 每条必须关联到具体 AC 编号 + 执行级别，示例：`AC-HOM-FN-01 @happy: ...（unit+integration级）`
> - 禁止模糊写法："从平台API获取"、"展示应用列表"、"性能良好"、"模块单测"

> **迭代标识**：绑 SRS 需求版本号，SRS 不变标识不变。同份需求拆 100 遍迭代标识相同，不用担心重复。`日期`仅记录拆分操作时间，不承担批次区分职责。
>
> **验收标准验证方式（五选一）**：`test_case_ref`（用例编号引用）、`design_doc_ref`（设计文档引用）、`inline_gwt`（内联 Given-When-Then）、`inline_criteria`（内联通用判据）、`reuse_baseline`（复用既有基线）。
>
> **参考字段 v4.3 升级**：每个 Story 的参考表必须完整覆盖其用到的全部设计输入文档——PRD、业务领域设计、HLD、DLD、交互稿、UI稿、API文档、验收标准、自测用例。每个字段必须标明来源于哪个文档的哪个章节。

### Step 3.5：设计文档完整映射（强制）

每个 Story 必须完整关联其所涉及的全部设计输入文档：

#### 映射要求

| 字段 | 0-1 | 1-N | 说明 | 示例 |
|------|:---:|:---:|------|------|
| `prd` | ✅ | ✅ | PRD/SRS 文档 + `§章节号 章节名` | `SRS_V1.2.docx §2.3 Banner组件` |
| `domain` | ✅ | ✅ | 业务领域设计 + `§章节` | `领域设计.md §3 鉴权上下文` |
| `hld` | ✅ | ✅ | 概要设计 + `§章节` | `概要设计.md §6 鉴权模块` |
| `dld` | ✅ | ✅(增量) | 详细设计 + `§章节` | `详细设计.md §feature-banner` |
| `interaction` | ✅ | ✅(增量) | 交互文档 + `§章节 + 规则编号` | `首页交互设计.md §3 RULE-HOME-001~010` |
| `ui_assets` | ✅ | ✅(增量) | UI设计稿 + 页面名称 + 区域 | `应用商店UI设计概览.md 首页/Banner区` |
| `api` | ❌ | ❌ | API文档 + `§接口名` | `API文档.md §/api/banner/list` |
| `ac` | ✅ | ✅ | 验收标准 + 用例编号 | `验收标准.md TC-HOM-BNR-001` |
| `self_test` | ✅ | ✅ | 自测用例 + 用例编号 | `自测用例.md TC-HOM-BNR-001-S` |

#### 映射质量要求

1. **有 UI 的 Story**：`interaction` 标注到**规则编号级**，`ui_assets` 标注到**页面名+区域**。两者缺一不可。
2. **纯后台 Story**：`interaction` 和 `ui_assets` 显式标注 `（纯后台任务，无独立UI）`，**不可留空**。
3. **每个字段溯源**：功能/场景/输入/输出/约束/验收标准——每个字段的内容都应能在参考表对应文档中找到原文出处。
4. **0-1 场景**：`prd` + `domain` + `hld` + `dld` + `interaction` + `ui_assets` + `ac` + `self_test` ——8 项全部必填（若有涉及）。

### Step 4：标记责任与依赖
- `responsibility`：frontend / backend / integration / config / infra
- `dependencies`：显式声明前置 Story ID

### Step 5：输出并过 Gate
输出到 `persistent-assets/spec-tasks/`，全部 `spec_ready: true` 才可进入 Specify。

### Step 6：拆分后验证（v4.5 新增）

**所有 Story 写入完成后，必须执行以下三项验证**，不得跳过：

#### 6.1 RTM 覆盖率验证
对照 `requirements-traceability-matrix.md` 逐条检查：
- 每个 In-Scope 条目是否被**恰好一个** Story 作为主要承载方？
- 每个业务规则 (R#) 是否出现在至少一个 Story 的"约束"字段？
- 是否有 Story 在 RTM 中找不到对应条目？（→ 多余拆分）

#### 6.2 AC 全集覆盖验证
提取全部 Story 的 `acceptance_criteria.items` 中的 AC 编号，与 AC 全集做集合运算：
- 全集 - 已覆盖 = 遗漏的 AC（→ 补充到对应 Story）
- 两个以上 Story 重复引用同一 AC（→ 粒度冗余，合并为一个）

#### 6.3 实施就绪检查
抽样检查 20% 的 Story（至少 5 个），逐项打勾：

```markdown
## 实施就绪检查 (Definition of Ready) — 每个 Story 必须全部 ✅

- [ ] input.source 含 DLD §章节号 + 接口名 + 参数类型
  ✅ 好: `DLD §4.7.3 接口1 fetchAppList(category: String?): Result<AppListDto>`
  ❌ 差: "从平台API获取应用列表"

- [ ] output.result 含响应类型/数据结构
  ✅ 好: `StateFlow<UiState>(Loading/Cached/Loaded/Empty/Error)`
  ❌ 差: "展示应用列表"

- [ ] constraints 至少 1 条含量化指标
  ✅ 好: "冷启动 95%分位 ≤3000ms (HLD §11 NFR)"
  ❌ 差: "性能良好"

- [ ] acceptance_criteria.items 每条含 AC 编号 + 执行级别
  ✅ 好: "AC-HOM-FN-01 @happy: observeAppList → Cached(≤50ms)→Loaded(30s内) (unit+integration级)"
  ❌ 差: "列表加载正常"

- [ ] dependencies 显式声明前置 Story ID（无隐含依赖）
```

**不合格处理**: 任一项未通过 → 必须回到 Step 3 补充该 Story 的内容。

---

## 输出目录

```
persistent-assets/spec-tasks/
 ├─ decomposition_index.yaml              # 全局索引
 ├─ overview.md                           # 拆分总览
 ├─ function_tree.md                      # 模块→功能组功能树
 ├─ requirements-traceability-matrix.md   # 需求可追溯矩阵（RTM，v4.5 新增）
 ├─ quality-assurance-strategy.md         # 质量保障策略说明（v4.5 新增）
 └─ stories/STORY-{MOD}-NNN/
      ├─ README.md                        # Speckit 唯一输入（纯 Markdown 九字段正文）
      └─ references/                      # 设计摘录
```

> **Story ID 命名规范**：`STORY-{MODULE_SHORT}-{NNN}`，如 `STORY-AUTH-001`、`STORY-HOM-001`。
> 模块缩写见 `decomposition_index.yaml` 中 `modules[].id` 的 `MOD-` 后缀部分（AUTH/HOM/DTL/CAT/SCH/DL/UPD/PERM/MN/MALL/CAB/VOI）。
> 完整结构规范见 `references/output-structure-spec.md`

---

## Story README 模板

> README.md 是 **Speckit 唯一输入**，采用纯 Markdown 格式（九字段正文），无需 YAML frontmatter。

```markdown
# STORY-{MOD}-NNN <功能组名称>

> 模块: {{module}}
> 功能组: {{functional_group}}
> 迭代标识: {{iteration_id}}
> 拆分日期: {{YYYY-MM-DD}}
> 责任方: {{responsibility}}
> 依赖: {{dependencies}}
> spec_ready: true

## 功能
{{一句话描述功能目标}}

## 场景
{{从哪里进入 → 做什么操作 → 看到什么结果}}

## 输入
- 数据: {{接收数据+字段说明}}
- 来源: {{DLD §章节 接口名(参数类型): 返回类型}}  ← v4.5: 必须精确到接口级

## 输出
- 结果: {{产出结果 + 响应类型/数据结构}}  ← v4.5: 必须含类型信息
- 展示: {{展示方式}}

## 约束
- {{至少一项含量化指标的约束}}  ← v4.5: 如 "≤3000ms"、"APK≤30MB"

## 验收标准
{{五选一验证方式，每条含 AC 编号 + 执行级别}}

## 迭代标识
{{IT-Vx.y}}

## 日期
{{YYYY-MM-DD}}

## 参考

| 类型 | 来源 |
|------|------|
| 需求 | {{PRD/SRS文档路径 §章节号 章节名}} |
| 领域 | {{业务领域设计文档路径 §章节号}} |
| 概要设计 | {{HLD文档路径 §章节号}} |
| 详细设计 | {{DLD文档路径 §章节号}} |
| 交互 | {{交互设计文档路径 §章节/规则编号（如 RULE-HOME-001）}} |
| UI | {{UI设计稿路径 页面名称（如 首页/Banner区）}} |
| API | {{API文档路径 §接口名}} |
| 验收 | {{验收标准文档路径 用例编号}} |
| 自测 | {{自测用例文档路径 用例编号}} |
```

> v4.3: 参考为完整结构化溯源表，0-1 场景全部 8 项（需求/领域/HLD/DLD/交互/UI/API/验收/自测）有则必填，每项标注到§章节级。每个字段的功能/场景/输入/输出/约束/验收标准内容均应能在参考表中找到原文出处。
> 
> **v4.5 新增**: `input.source` 强制含 DLD §接口名+参数类型；`output.result` 强制含响应类型；`constraints` 至少 1 条含量化指标；`acceptance_criteria.items` 强制含 AC 编号+执行级别。不符合者标记"不可实施"。

---

## 错误路径（禁止事项）

| # | 禁止 | 原因 |
|---|------|------|
| 1 | 拆分阶段修改需求/交互设计 | 设计已冻结 |
| 2 | 将"开发任务清单"当需求拆分 | 任务清单 ≠ 工程拆分 |
| 3 | 以技术组件为拆分起点 | 应从功能组出发 |
| 4 | 将未验证假设拆成工程项 | 假设不可直接工程化 |
| 5 | 九字段出现模糊描述 | "尽量""可能""合理" |
| 6 | 多正交功能混在同一 Story | "并且/同时/或"→拆分 |
| 7 | 跨模块混合 | 一个 Story 只属一个模块 |
| 8 | 九字段拷贝粘贴 | 每个 Story 差异化 |
| 9 | **功能组再向下细分** | 功能组是最终拆分单位 |
| 10 | 用日期区分需求批次 | 日期是执行时间戳→同份需求隔天拆误判为两期 |
| 11 | **参考字段只有文档名，无章节号/规则编号/页面名** | 无法定位原文——需求必须到§章节、交互到规则编号、UI到页面名 |
| 12 | **纯后台 Story 的交互/UI参考留空** | 必须显式标注"纯后台任务，无独立UI"，不可留空 |
| 13 | **0-1场景缺少设计文档引用** | 0-1 场景 domain/hld/dld/self_test 有则必填，不得跳过 |
| 14 | **批量脚本/模板生成 Story**（v4.4 新增） | 批量脚本产出的 README.md 必有空白占位符。每个 Story 必须从对应的设计文档章节中**单独提取**内容，不可套用模板批量生成 |

> 完整反模式见 `references/anti-patterns.md`

---

## Stop Sign（终止条件）/ 质量门禁

1. 每个 Story 至少关联一个测试 Case
2. 八个必填字段（功能/场景/输入/输出/约束/验收标准/迭代标识/日期）完整且确定
3. `spec_ready: true` 覆盖率 100%
4. 功能树完整覆盖全部 AC
5. 场景类型与拆分策略一致
6. **功能组为最小拆分单位，未再细分**
7. 同一批次所有 Story 的 `迭代标识` 一致，且与 `decomposition_index.yaml` 根级一致
8. **（v4.2）** 参考字段结构化：有UI的Story `interaction`含规则编号 + `ui_assets`含页面名；纯后台显式标注原因
9. **（v4.3）** 0-1 场景全部设计文档（prd/domain/hld/dld/interaction/ui_assets/ac/self_test）有则必填，每项标注到§章节级
10. **（v4.4 新增）** README.md 内容完整性：九字段（功能/场景/输入/输出/约束/验收标准/迭代标识/日期/参考）不得为空字符串或模板占位符（如 `TODO`、`Ref README.md`）
11. **（v4.5 新增）RTM 覆盖率**: 全部 PRD In-Scope 条目 + 全部业务规则 R# + 全部 AC 用例编号 → 必须在 RTM 中有 1:1 Story 映射（`requirements-traceability-matrix.md`）
12. **（v4.5 新增）AC 全集覆盖**: 验收标准文档中的全部 AC 编号必须出现在至少一个 Story 的 `acceptance_criteria.items` 中；不应有未引用的 AC
13. **（v4.5 新增）DLD 接口绑定**: 每个 Story 的 `input.source` 必须包含 DLD §章节号 + 接口名 + 参数类型；`output.result` 必须含响应类型/数据结构；禁止"从平台API获取"等模糊写法
14. **（v4.5 新增）约束可量化**: 每个 Story 的 `constraints` 至少含 1 条带数值的指标（如 ≤3000ms、≤30MB、95%分位）
15. **（v4.5 新增）依赖完整性**: 每个 Story 的 `dependencies` 字段显式声明前置 Story ID，不允许仅靠文档中的叙述暗示依赖关系；不允许循环依赖

> 完整门禁清单见 `references/quality-gate-checklist.md`

---

## 常见问题

### 拆分粒度怎么把握？
以**功能组**为单位。比如"首页"模块下，`Banner` 是一个功能组，`应用推荐`是一个功能组，`应用分类`是一个功能组——每个功能组就是一个 Story，不再进一步拆分。

### 如何区分一期和二期？
通过 **迭代标识** 字段。一期需求文档（SRS V1.0）拆分时所有 Story 的迭代标识 = `IT-V1.0`。二期有新需求文档时，迭代标识 = `IT-V1.1`。**日期**仅记录拆分执行时间，不作批次区分——同份需求在不同天拆分迭代标识相同，不会被误判。

### 同份需求隔天再拆一遍会重复吗？
**不会**。迭代标识绑定 SRS 版本，同一份需求文档的迭代标识始终相同。0-1 场景拆 10 遍只要用同一份 SRS，迭代标识都是 `IT-V1.0`。`decomposition_index.yaml` 通过迭代标识去重，不会多出 Story。

### 1-N 场景如何避免重复拆分？
先读取 `decomposition_index.yaml` 获取既有 Story 列表和其迭代标识，只对增量功能生成新 Story（新迭代标识），增量 Story 的 dependencies 可指向既有 Story。

### 参考字段的章节级溯源标注到什么粒度？（v4.2 新增）
- `prd`：需求文档路径 + §章节号 + 章节名（如 `SRS_V1.2.docx §2.3 Banner组件`）
- `interaction`：交互文档路径 + §章节 + **规则编号级**（如 `RULE-HOME-001~010`）
- `ui_assets`：UI设计稿路径 + **页面名称级**（如 `首页`、`详情页-半屏`）

只写文档名不写章节号/规则编号/页面名 → 无法追溯到原文 → 不通过门禁。

### 纯后台 Story 没有 UI 怎么办？
交互和 UI 两项**不可留空**，必须显式标注原因：
- 纯后台：`（纯后台任务，无独立UI交互文档）` 、 `（无独立UI展示——对车主透明）`
- 系统层：`（系统层面控制，无直接UI交互文档）` 、 `（无独立UI展示——对车主近乎透明）`

### 0-1 场景需要引用全部设计文档吗？（v4.3 新增）
**是的**。0-1 场景要求完整的可追溯链：`prd`(需求) + `domain`(领域) + `hld`(概设) + `dld`(详设) + `interaction`(交互) + `ui_assets`(UI) + `ac`(验收) + `self_test`(自测)。每个 Story 中每个字段的内容都应能在参考表中找到对应的文档章节出处。

### Story 字段与参考表的关系是什么？
参考表是"谁说了什么"的索引。功能→prd§章节、场景→prd§章节+interaction§规则、输入→dld§接口、输出→dld§响应+interaction§规则、约束→hld§架构、验收标准→ac+self_test。审查者通过参考表可一步定位到任何字段的原始设计依据。

### 生成大量 Story 时如何保证每个都完整？（v4.4 新增）
**禁止**用批量脚本/模板一次性生成所有 Story 的 README.md。必须**逐个 Story**从对应的设计文档章节中提取内容：
1. 需要 20 个 Story → 逐个写入，不是 write 一个循环
2. 每个 Story 完成后自查：`scenario_desc` 是否描述了完整操作路径？`input` 是否标注了具体接口和数据字段？`constraints` 是否含技术栈+性能+安全+车机？`acceptance_criteria` 是具体的 GWT 还是空洞的"Ref README"？
3. 检查 README.md 中无 `""` 空字符串、无 `TODO`、无 `Ref README.md` 等占位符
4. 最后一个 Story 写完后再统一过质量门禁

### AI 每次拆分输出不一样，怎么保证可靠性？（v4.5 新增）
**可靠性不靠"让 AI 输出一样"，而靠三个外部锚点约束**：
1. **RTM 固定锚点**（防偏离）：PRD In-Scope 条目 + 业务规则 R# 是客观存在的不可变参照点。每次拆分完逐行对照——哪个条目没有 Story 对应，就是遗漏。
2. **AC 独立验证集**（防遗漏）：验收用例（AC）是独立于拆分流程的第三方文档。全部 AC 编号必须出现在 Story 中。遍历检查，未出现即遗漏。
3. **上次拆分做锚点**（防结构漂移）：若是对同一份 SRS 重新拆分，把上次的 `decomposition_index.yaml` 作为输入，约束 AI"保持模块边界不变，仅调整与设计修订相关的部分"。

### 怎么判断一个 Story 写到了"可实施"的程度？（v4.5 新增）
用"实施就绪检查清单"（见 Step 6.3），五项全部通过才算可实施：
- `input.source` 引用到了 DLD 的哪个接口？参数类型是什么？
- `output.result` 明确了响应数据结构吗？
- `constraints` 有量化指标吗？（不能只是"性能良好"）
- `acceptance_criteria` 关联到了具体 AC 编号吗？
- `dependencies` 显式声明了前置 Story ID 吗？

---

## 参考文件

| 路径 | 用途 |
|------|------|
| `references/methodology-core.md` | 拆分方法论 + 九字段原则详解 |
| `references/scenario-guide.md` | 0-1/1-N/Bugfix 场景策略 |
| `references/quality-gate-checklist.md` | 质量门禁检查清单 |
| `references/anti-patterns.md` | 禁止事项详情 |
| `references/output-structure-spec.md` | 输出目录结构规范 |
| `references/quality-assurance-strategy.md` | 质量保障三层防线完整策略（v4.5 新增） |
| `references/rtm-template.md` | RTM 可追溯矩阵模板（v4.5 新增） |
| `assets/` | 输出模板 |
