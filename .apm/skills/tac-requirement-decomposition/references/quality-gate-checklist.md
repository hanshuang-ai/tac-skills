# 质量门禁检查清单（Quality Gate Checklist）

> 来源: SKILL.md §5
> 版本: v4.4

---

## Gate 1~7

测试用例覆盖 / 九字段完整性 / 独立可实现性 / 工程动作明确 / Spec-Ready全覆盖 / 无UI污染 / 无技术实现泄漏

（略——完整定义见 SKILL.md）

---

## Gate 8：功能树完整性

所有 AC 映射到 Story，无遗漏功能组。

---

## Gate 9：迭代标识一致性

同批次所有 Story 迭代标识一致，与 `decomposition_index.yaml` 一致。

---

## Gate 10：参考字段结构完整性

| 检查项 | 要求 |
|--------|------|
| `prd` | 文档路径 + §章节号 + 章节名 |
| `domain` | 0-1 必填：文档 + §章节 |
| `hld` | 0-1 必填：文档 + §章节 |
| `dld` | 0-1 必填：文档 + §章节 |
| `interaction` | 有UI时含规则编号；纯后台显式标注原因 |
| `ui_assets` | 有UI时含页面名；纯后台显式标注原因 |
| `ac` | 文档 + 用例编号 |
| `self_test` | 0-1 必填：文档 + 用例编号 |
| `api` | 可选：文档 + §接口名 |

---

## Gate 11：字段→文档可追溯

Story 中每个字段（功能/场景/输入/输出/约束/验收标准）的内容在参考表中能找到对应的文档章节出处。审查者可通过参考表一步定位到原始设计依据。

---

## Gate 12：README.md YAML frontmatter 内容完整性（v4.5）

```yaml
check:
  scenario_desc → 非空，描述完整操作路径（禁止 ""）
  input.data → 非空，标注具体数据字段（禁止 ""）
  input.source → 非空，标注接口名/数据来源（禁止 ""）
  output.result → 非空，描述产出结果（禁止 ""）
  output.display → 非空，描述展示方式（禁止 ""）
  constraints → 至少含技术栈+性能+安全/车机 3 项（禁止仅一项泛泛约束）
  acceptance_criteria.items → 内联 GWT 或具体用例编号（禁止 "Ref README" 等占位符）
  function → 非空且非 "TODO" 等占位符
```

---

## 自检输出

```yaml
self_check:
  scenario: "0-1" | "1-N" | "bugfix"
  iteration_id: "IT-Vx.y"
  date: "YYYY-MM-DD"
  test_case_coverage: 100%
  nine_field_completeness: 100%
  iteration_id_consistency: true
  reference_structure_valid: true
  field_document_traceable: true    # v4.3 新增
  spec_ready_coverage: 100%
  blocking_issues: []
```
