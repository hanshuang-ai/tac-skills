# tac-requirement-decomposition SKILL 使用指南

> 版本：v4.5（2026-06-02）
> 用途：使用需求拆分 SKILL 进行 0-1 / 1-N / Bugfix 三种场景的工程化需求拆分

---

## 1. 快速总览

| 场景 | 一句话定义 | Story 数 | 迭代标识 |
|------|-----------|:---:|:---:|
| **0-1** | 从零构建 | 5-50+ | `IT-V1.0`（全同） |
| **1-N** | 在既有产品上增量迭代 | 1-10 | 新批次标识（如 `IT-V1.1`） |
| **Bugfix** | 修复缺陷 | 1-3 | 沿用原批次标识 |

---

## 2. 命令格式

在对话中输入以下命令即可触发 SKILL：

```
@command://tac-requirement-decomposition  <场景信号> <补充说明>
```

### 场景信号

| 触发词 | 场景 |
|--------|:----:|
| "新项目""从零开发""全新模块""0-1拆分" | 0-1 |
| "新增""迭代""二期""增强""1-N拆分" | 1-N |
| "修复""bug""crash""报错""崩溃""异常""Bugfix" | Bugfix |

### 触发示例

```
# 0-1
@command://tac-requirement-decomposition 根据当前项目文档进行0-1的需求拆分

# 1-N
@command://tac-requirement-decomposition 对 AppStore 做二期拆分，新增搜索过滤和评分功能，基于 persistent-assets/spec-tasks/decomposition_index.yaml

# Bugfix
@command://tac-requirement-decomposition 修复下载队列暂停后继续未回队尾的 Bug
```

---

## 3. 0-1 场景（从零构建）

### 3.1 必须准备的设计文档

| # | 文档 | 说明 |
|---|------|------|
| 1 | **PRD / SRS（冻结版）** | 完整需求规格说明书 |
| 2 | **业务领域设计** | 限界上下文、业务规则、聚合根 |
| 3 | **HLD 概要设计** | 技术栈选型、模块划分、架构视图 |
| 4 | **DLD 详细设计** | 各模块接口契约、状态机、数据模型 |
| 5 | **AC 验收标准** | 验收用例（含 happy / error / 状态机 / NFR） |
| 6 | **交互设计稿** | 页面交互规则（至少 5 个主要页面） |
| 7 | **UI 设计稿** | 页面视觉稿（截图 / MasterGo DSL） |
| 8 | **需求验证结论** | 设计评审通过记录 |

**缺失任一项且不允许推断 → SKILL 会拒绝执行，输出缺失清单。**

### 3.2 输出结果

```
persistent-assets/spec-tasks/
├── decomposition_index.yaml   # 全局索引（后续 1-N/Bugfix 依赖它）
├── overview.md                # 拆分总览
├── function_tree.md           # 模块 → 功能组 功能树
└── stories/
    ├── STORY-XXX-001/
    │   ├── README.md          # Speckit 唯一输入（YAML frontmatter + Markdown 正文）
    │   └── references/        # 设计摘录
    └── ...
```

### 3.3 拆分粒度规则

> **模块 → 功能组 = Story，功能组是最小拆分单位，不再向下细分。**

```
首页 (模块)
├── Banner运营位          ← 功能组 = Story 1
├── 应用推荐              ← 功能组 = Story 2
├── 应用分类预览          ← 功能组 = Story 3
└── 搜索入口 + 下载提示    ← 功能组 = Story 4
```

### 3.4 本项目的 0-1 拆分实例

AppStore 车机应用商店 0-1 拆分产生了：

| 指标 | 值 |
|------|---|
| 模块 | 15 |
| Story | 40 |
| 迭代标识 | IT-V1.0 |
| 输出文件 | 44（40 README.md + 4 结构文件） |

---

## 4. 1-N 场景（增量迭代）

### 4.1 必须准备的设计文档

| # | 文档 | 宽松条件 |
|---|------|---------|
| 1 | **PRD 增量需求（冻结版）** | 必须 |
| 2 | **业务领域设计** | 仅增量部分 |
| 3 | **HLD 概要设计** | 仅增量涉及的部分 |
| 4 | **DLD 详细设计（增量）** | 新增模块/接口需要 |
| 5 | **AC 验收标准** | 增量部分用例 |
| 6 | **交互 & UI 验收稿（增量）** | 新增页面需要 |
| — | **`decomposition_index.yaml`** | **必须存在**（定位既有 Story） |

### 4.2 最小允许集

如果增量功能**不涉及新页面、新模块、新业务规则**：

```
必需：PRD 增量 + DLD 增量接口 + AC 用例 + decomposition_index.yaml
可省略：domain / HLD / 交互稿 / UI 稿
```

### 4.3 最佳描述模板

```
场景：1-N 增量拆分
基于：persistent-assets/spec-tasks/decomposition_index.yaml
增量功能：
  1. 新增搜索过滤（按分类/评分/价格）
  2. 新增应用评分功能
不涉及模块：下载模块 / 授权流程 / 座舱适配
新迭代标识：IT-V1.1
```

### 4.4 SKILL 会做什么

1. 读取 `decomposition_index.yaml`，获取既有 Story 列表
2. 在功能树上标注 `[IT-V1.0]`（既有）和 `[IT-V1.1 新增]`（增量）
3. 只拆增量部分的新 Story
4. 增量 Story 的 `dependencies` 可指向既有 Story
5. 标注兼容性约束（不破坏既有功能）

---

## 5. Bugfix 场景（缺陷修复）

### 5.1 必须准备的文档

| # | 文档 | 说明 |
|---|------|------|
| 1 | **缺陷单（冻结版）** | 必须含 **现象 / 预期 / 复现步骤** 三要素 |
| 2 | **AC 验收标准** | 修复后的回归验证用例 |
| 3 | **`decomposition_index.yaml`** | 定位受影响 Story |
| — | **DLD / HLD** | 仅在修复涉及架构变更时需要 |

### 5.2 最佳描述模板

```
场景：Bugfix
受影响 Story：STORY-DL-003（队列推进与中断恢复）
现象：下载中任务暂停后点击继续，任务没有回到队列末尾排队，而是直接变为下载中
预期：暂停任务点击继续后应回到队列末尾排队，等待前面任务完成后再执行
复现步骤：
  1. 同时下载 3 个应用
  2. 暂停第一个下载中的应用
  3. 点击该待续任务的"继续"按钮
  4. 观察队列：任务直接开始下载（未排队）
原始迭代标识：IT-V1.0
```

### 5.3 SKILL 会做什么

1. 分析缺陷单 → 提取 现象/预期/复现 三要素
2. 从 `decomposition_index.yaml` 定位受影响 Story
3. 拆出 1 个修复 Story（场景含复现路径）
4. 迭代标识沿用原始批次，日期 = 当前

---

## 6. 输入检查清单

在触发 SKILL 前，逐项确认：

| 项 | 0-1 | 1-N | Bugfix |
|----|:---:|:---:|:------:|
| 需求文档已冻结 | ✅ | ✅ | ✅ |
| 业务领域设计可获取 | ✅ | ✅(增量) | 可选 |
| HLD 可获取 | ✅ | ✅ | 可选 |
| DLD 可获取 | ✅ | ✅(增量) | 可选 |
| AC 验收标准已产出 | ✅ | ✅ | ✅ |
| 交互/UI 验收稿可获取 | ✅ | ✅(增量) | 条件 |
| `decomposition_index.yaml` 存在 | N/A | ✅ | ✅ |

---

## 7. 注意事项

### 7.1 不要做的事情

- ❌ 不要把 `spec.md`（Speckit 下游产物）当作输入——那是拆分输出后由 Specify 阶段产生的
- ❌ 不要在 1-N/Bugfix 时删除或重建 `decomposition_index.yaml`——这是后续迭代的唯一基准
- ❌ 不要用"完善""优化""改进"等模糊词描述——SKILL 需要具体的功能边界

### 7.2 缺失输入怎么办

SKILL 在 `Step 1` 就会检查输入完整性。如果文档缺失：

- **缺失不可推断项** → SKILL 拒绝执行，输出缺失清单
- **缺失可选项** → SKILL 会标注"推断"并继续，但建议后续补齐

### 7.3 重复执行

- 同份需求在不同日期执行 0-1 拆分：迭代标识不变（IT-V1.0），日期变化
- `decomposition_index.yaml` 通过迭代标识去重，不会产生重复 Story
- 1-N 拆分前先读 index.yaml，只拆增量

---

## 8. 关联工具链

| 阶段 | 工具 / Skill | 关系 |
|------|-------------|------|
| 需求验证 | 业务方评审 | 上游 → 产出冻结版需求文档 |
| **需求拆分** | **tac-requirement-decomposition** | **本 SKILL** |
| 规格编写 | Speckit / Specify (`/speckit.specify`) | 下游 → 消费 README.md YAML frontmatter |
| 实现计划 | Speckit Plan (`/speckit.plan`) | 下游 |
| 任务拆分 | Speckit Tasks (`/speckit.tasks`) | 下游 |
| TDD 实现 | tdd-implementer agent | 下游 |

---

## 9. 快速参考卡

```
┌──────────────────────────────────────────────────────┐
│  tac-requirement-decomposition SKILL v4.4            │
├──────────────────────────────────────────────────────┤
│  触发命令: @command://tac-requirement-decomposition  │
│  拆分粒度: 模块 → 功能组（功能组 = Story，不细分）    │
│  输出目录: persistent-assets/spec-tasks/                    │
│  关键文件: decomposition_index.yaml（迭代锚点）       │
│                                                      │
│  0-1:  全量设计文档 → 全量拆分                        │
│  1-N:  增量设计 + index.yaml → 只拆增量               │
│  Bug:  缺陷单(现象/预期/复现) + index.yaml → 单Story  │
│                                                      │
│  门禁: spec_ready: true 100% 必须                    │
│  禁止: 批量脚本生成 Story / 输入用 spec.md            │
└──────────────────────────────────────────────────────┘
```
