# Requirement Decomposition Overview

> 迭代标识: {{iteration_id}}
> 拆分日期: {{date}}
> SKILL 版本: v4.3
> 场景类型: {{scenario_type}}（0-1 / 1-N / Bugfix）
> {{story_count}} 个 Story，全部 spec_ready = true

---

## 场景信息

- **迭代标识**: {{iteration_id}}
- **拆分日期**: {{date}}
- **原始需求**: {{requirement_id}} {{requirement_title}}

---

## 设计输入

| # | 输入项 | 路径 | 状态 |
|---|--------|------|------|
| 1 | 需求设计产物 | {{prd_path}} | ✅ |
| 2 | 业务领域设计 | {{domain_path}} | ✅ |
| 3 | 概设 | {{hld_path}} | ✅ |
| 4 | 详设 | {{dld_path}} | ✅ |
| 5 | 验收标准 | {{ac_path}}（~{{ac_count}}条） | ✅ |
| 6 | 自测用例 | {{self_test_path}}（~{{st_count}}条） | ✅ |
| 7 | 交互&视觉稿 | {{interaction_path}} | ✅ |

---

## 功能总览

```
{{#each modules}}
┌─ {{name}} ({{story_count}} Stories)
{{#each stories}}
│  ├─ {{story_id}} {{title}} `{{iteration_id}}`
{{/each}}
{{/each}}
```

---

## Story 列表

| Story ID | 模块 | 功能组 | 功能 | 迭代 | 日期 | Resp | Deps |
|----------|------|--------|------|:---:|------|------|-----|
{{#each stories}}
| {{story_id}} | {{module}} | {{title}} | {{function}} | {{iteration_id}} | {{date}} | {{resp}} | {{deps}} |
{{/each}}

---

## 执行顺序

```
第 1 批（无依赖）:
{{#each batch_1}}
  - {{story_id}} {{title}}
{{/each}}
第 2 批:
{{#each batch_2}}
  - {{story_id}} {{title}}（依赖: {{deps}}）
{{/each}}
```

---

## 下游交接

| 消费方 | 说明 |
|--------|------|
| Speckit/Specify | 读取 `stories/<Story-ID>/README.md`（YAML frontmatter） |
| 人类工程师 | 读取 `stories/<Story-ID>/README.md`（Markdown 正文） |
| CI/CD | 读取 `decomposition_index.yaml` |
| 评审 | 读取 `function_tree.md` |
