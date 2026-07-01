# 输出目录结构规范（Output Structure Spec）

> 来源: SKILL.md §4
> 版本: v4.5
> 用途: 确保拆分的全部产出物符合标准目录结构，含九字段 + 迭代标识 + 设计文档完整溯源。README.md 采用 YAML frontmatter + Markdown 正文双格式，是 Speckit 唯一输入。

---

## 根目录结构

```
persistent-assets/spec-tasks/
 ├─ decomposition_index.yaml
 ├─ overview.md
 ├─ function_tree.md
 └─ stories/<Story-ID>/
      ├─ README.md       # Speckit 唯一输入（YAML frontmatter + Markdown 正文）
      └─ references/     # 原始文档摘录
```

---

## Story 级 README.md 参考表格式（v4.3）

```markdown
## 参考

| 类型 | 来源 |
|------|------|
| 需求 | {{PRD §章节号 章节名}} |
| 领域 | {{业务领域设计 §章节}} |
| 概要设计 | {{HLD §章节}} |
| 详细设计 | {{DLD §章节}} |
| 交互 | {{交互文档 §章节/规则编号}} |
| UI | {{UI设计稿 页面名称}} |
| API | {{API文档 §接口名}} |
| 验收 | {{验收标准 用例编号}} |
| 自测 | {{自测用例 用例编号}} |
```

---

## README.md YAML frontmatter references 格式（v4.5）

> references 字段嵌入 README.md 的 YAML frontmatter 中，参考格式如下：

```yaml
references:
  prd: "{{PRD/SRS文档路径 §章节号 章节名}}"
  domain: "{{业务领域设计文档路径 §章节号}}"
  hld: "{{概要设计文档路径 §章节号}}"
  dld: "{{详细设计文档路径 §章节号}}"
  interaction: "{{交互设计文档路径 §章节/规则编号}}"
  ui_assets: "{{UI设计稿路径 页面名称}}"
  api: "{{API文档路径 §接口名}}"
  ac: "{{验收标准文档路径 用例编号}}"
  self_test: "{{自测用例文档路径 用例编号}}"
```

---

## 校验规则

| # | 校验项 |
|---|--------|
| 1 | 根目录结构完整 |
| 2 | 每个 Story 含 README.md（YAML frontmatter 完整） |
| 3 | 所有 Story spec_ready = true |
| 4 | 8 个必填字段非空 |
| 5 | Speckit 可直接读取 README.md YAML frontmatter |
| 6 | 同批次迭代标识一致 |
| 7 | references 至少含 prd+domain+hld+dld+ac+self_test（0-1） |
| 8 | 每个字段内容可在参考表中追溯原文出处 |

> 任一不满足 → 拆分失败，禁止进入 Specify。
