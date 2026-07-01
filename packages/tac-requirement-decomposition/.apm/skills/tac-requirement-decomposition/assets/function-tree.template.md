# 功能分解树

> 迭代标识: {{iteration_id}}
> 拆分日期: {{date}}
> 场景类型: {{scenario_type}}（0-1 / 1-N / Bugfix）
> 拆分粒度: 模块 → 功能组（功能组 = Story）
> SKILL 版本: v4.3

---

{{#each modules}}
## 模块: {{name}} `{{story_count}} Stories`

| Story ID | 功能组 | 功能 | 迭代 | 日期 | 优先级 | Responsibility | Deps |
|----------|--------|------|:---:|------|--------|----------------|------|
{{#each stories}}
| {{story_id}} | {{title}} | {{function}} | {{iteration_id}} | {{date}} | P{{priority}} | {{responsibility}} | {{dependencies_str}} |
{{/each}}

{{/each}}

---

## 覆盖矩阵

| AC ID | 描述 | 对应 Story | 覆盖 |
|-------|------|-----------|:--:|
{{#each ac_coverage}}
| {{ac_id}} | {{description}} | {{story_id}} | ✅ |
{{/each}}

---

## 执行建议

```
第 1 批（无依赖，并行）:
{{#each batch_1}}
  - {{story_id}} {{title}} [{{module}}]
{{/each}}

第 2 批:
{{#each batch_2}}
  - {{story_id}} {{title}} [{{module}}] ← 依赖: {{deps}}
{{/each}}
```
