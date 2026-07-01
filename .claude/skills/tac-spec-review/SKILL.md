---
name: "tac-spec-review"
version: 0.4.5
description: "Speckit 流程的 Review Gate 执行器，按项目专项规范审查 spec.md / plan.md 并输出二值闸门结论。触发：Speckit 流程中 Review Gate 节点。所在环节：② 规格化 / ③ 技术设计。"
user-invocable: true
---

## 适用范围

本 Skill 只检查**项目专项规范层**的合规（中文、车机场景、功能点分析规范、PROJECT.md 场景映射引用完整性）。通用层检查（NEEDS CLARIFICATION 残留、宪章 MUST/SHOULD 冲突、跨工件一致性、覆盖映射）由 `/speckit-analyze` 负责，本 Skill 不重复。

## Step 1: 确定审查目标

确认要审查的文件：
1. 读取 `.specify/feature.json` 获取当前 feature 目录
2. 确认 `spec.md` 和/或 `plan.md` 存在

## Step 2: 审查 spec.md

**结构完整性：**
- [ ] User Scenarios & Testing 章节存在且有具体用户故事
- [ ] 每个用户故事有优先级标记（P1/P2/P3）
- [ ] 每个用户故事有 Acceptance Scenarios（Given/When/Then）
- [ ] 功能点分析映射章节存在（产品目标/核心场景/非范围目标/系统边界）
- [ ] Requirements 章节有编号的功能需求（FR-001 等）
- [ ] Success Criteria 章节有可度量的成功标准
- [ ] Edge Cases 章节已填写（不是模板占位符）

**项目专项规范合规：**
- [ ] 默认使用中文（宪章原则 II）
- [ ] 考虑了车机场景约束（宪章原则 III）
- [ ] 无实现细节泄漏（不提及具体框架、语言、API）

**功能点分析规范合规：**
- [ ] 明确了系统边界（本软件负责/不负责）
- [ ] 功能树至少三级（一级功能→二级功能→三级功能）
- [ ] 接口与非功能要求已填写

## Step 3: 审查 plan.md（如果存在）

### Step 3.1: 基础结构

- [ ] Constitution Check 章节存在且已勾选（不是空的 `- [ ]`）
- [ ] Technical Context 已填写（非模板占位符）
- [ ] Project Structure 已填写具体目录

### Step 3.2: 专项规范引用完整性（按 PROJECT.md 场景映射逐项核对）

读取仓库根目录 `PROJECT.md` 的「场景与必读文档映射」章节，按本次变更命中的场景**全集**（命中多个场景必须取并集，不得只取其一）列出对应的专项规范与相关文档清单。

逐项核对 plan.md 的「Applicable Constitutions / 宪章引用」章节：

- [ ] 命中场景对应的每一份专项规范文件路径都已出现在引用清单
- [ ] 同一变更命中多个场景时，对应的多份专项规范全部引用（不能只引用其中一份）

**不得在本 Skill 内固定列举专项规范条目**——映射以 `PROJECT.md` 当前内容为准，避免与单一文档真理源出现漂移。

缺失时按以下格式输出，便于直接补 plan.md：

```
- 命中场景：<PROJECT.md 中的场景描述原文>
- 应引用：<专项规范文件路径>
- 当前 plan.md：未引用 / 已引用
```

## Step 4: 输出审查结论

格式：

```
## Review Gate 审查结果

**审查文件**: specs/NNN-feature/spec.md
**审查时间**: YYYY-MM-DD
**结论**: 通过 / 需修改

### 通过项
- [x] ...

### 需修改项
- [ ] 问题描述 → 建议修改方式

### 建议
- ...
```

如果有需修改项，列出具体位置和修改建议，等用户修改后再次执行本 Skill 复查。
