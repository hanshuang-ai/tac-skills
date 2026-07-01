# {{story_id}} {{title}}

> 模块: {{module}}
> 功能组（即本 Story）: {{functional_group}}
> 迭代标识: {{iteration_id}}
> 拆分日期: {{date}}
> 场景类型: {{scenario}}（0-1 / 1-N / Bugfix）

---

## 功能

{{function}}

---

## 场景

{{scenario_desc}}

---

## 输入

- **数据**: {{input_data}}
- **来源**: {{input_source}}

---

## 输出

- **结果**: {{output_result}}
- **展示**: {{output_display}}

---

## 约束

{{#each constraints}}
- {{this}}
{{/each}}
{{#unless constraints}}
- 待补充
{{/unless}}

---

## 验收标准

{{#if test_case_ref}}
### 用例编号引用
{{#each test_case_ref_items}}
- {{this}}
{{/each}}
{{/if}}

{{#if design_doc_ref}}
### 设计文档引用
{{#each design_doc_ref_items}}
- {{this}}
{{/each}}
{{/if}}

{{#if inline_gwt}}
### Given-When-Then
{{#each inline_gwt_items}}
- **Given** {{given}} **When** {{when}} **Then** {{then}}
{{/each}}
{{/if}}

{{#if inline_criteria}}
### 通用判据
{{#each inline_criteria_items}}
- {{this}}
{{/each}}
{{/if}}

{{#if reuse_baseline}}
### 复用既有基线
{{#each reuse_baseline_items}}
- {{this}}
{{/each}}
{{/if}}

---

## 迭代标识

{{iteration_id}}

## 日期

{{date}}

---

## 参考

| 类型 | 来源 |
|------|------|
| 需求 | {{prd}} |
{{#if domain}}| 领域 | {{domain}} |
{{/if}}
{{#if hld}}| 概要设计 | {{hld}} |
{{/if}}
{{#if dld}}| 详细设计 | {{dld}} |
{{/if}}
| 交互 | {{interaction}} |
| UI | {{ui_assets}} |
{{#if api}}| API | {{api}} |
{{/if}}
| 验收 | {{ac}} |
| 自测 | {{self_test}} |

> 所有引用均标注到文档章节/规则编号/用例编号级。0-1 场景全部 8 项有则必填。每个字段功能/场景/输入/输出/约束/验收标准均可在参考表中找到原文出处。

---

## 附加信息

| 属性 | 值 |
|------|-----|
| **Owner** | {{owner}} |
| **Responsibility** | {{responsibility}} |
| **Dependencies** | {{dependencies_str}} |
| **测试用例** | {{test_cases_str}} |
| **Spec Ready** | ✅ |

---

> 本文件内容从已验收的设计阶段产物中提取，所有字段均为冻结状态。
