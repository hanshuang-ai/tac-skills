# 禁止事项（Anti-Patterns）

> 来源: SKILL.md §6
> 版本: v4.4

---

## #1~#8

禁止修改需求 / 以开发任务当拆分 / 以技术组件为起点 / 未验证假设当工程项 / 模糊描述 / 正交功能混合 / 跨模块混合 / 拷贝粘贴

（略——完整定义见 SKILL.md）

---

## #9 禁止 0-1 场景遗漏技术栈约束

| 正例 | 「约束」: "Kotlin + ViewBinding, Android 10+" |
| 反例 | 0-1 场景下「约束」为空

---

## #10 禁止功能组再向下细分

| 原因 | 功能组是最小拆分单位，如首页→Banner、应用推荐、应用分类各为一个 Story。 |

---

## #11 禁止用日期作为需求批次标识

| 原因 | 日期是执行时间戳，同份需求隔天重拆误判为两期。 |
| 正例 | 用 `迭代标识`（如 `IT-V1.0`）绑定 SRS 版本号 |

---

## #12 禁止参考字段仅标文档名不标章节/规则/页面

| 原因 | 无法定位原文。 |
| 正例 | `prd` → `SRS_V1.2.docx §2.3`、`interaction` → `交互设计.md §3 RULE-HOME-001` |
| 反例 | `prd` → `PRD.docx`（无§）、`interaction` → `交互设计.md`（无规则编号） |

---

## #13 禁止纯后台 Story 的交互/UI参考留空

| 原因 | 必须显式标注"纯后台任务，无独立UI"。 |

---

## #14 禁止 0-1 场景跳跃设计文档引用

| 严重级别 | **阻断** |
| 原因 | 0-1 从零构建，需要完整追溯链。prd/domain/hld/dld/interaction/ui_assets/ac/self_test 有则必填，不得跳过。 |
| 正例 | 参考表包含全部 8 项（或显式标注 N/A 及原因） |
| 反例 | 参考表只有 prd + ac 两项，domain/hld/dld/self_test 有空缺也未标注原因 |

---

## #15 禁止批量脚本/模板生成 Story（v4.4 新增）

| 严重级别 | **阻断** |
| 原因 | 批量脚本产出的 README.md 必然包含空字符串、`TODO`、`Ref README.md` 等占位符。每个 Story 的场景/输入/输出/约束/验收标准互不相同，必须从对应的设计文档章节中**逐个单独提取**。批量生成 = 空壳 Story。 |
| 正例 | 逐个 Story 读取对应的设计文档章节 → 提取具体内容 → 写入 README.md（YAML frontmatter）→ 自检无空值 |
| 反例 | 用一份模板 `foreach ($id in $ids) { write template }` → 全部 20 个 README.md 只有骨架（data: ""、scenario_desc: ""） |

---

## #16 禁止 README.md YAML frontmatter 存在占位符或空值（v4.5）

| 严重级别 | **阻断** |
| 原因 | `scenario_desc: ""`、`data: ""`、`items: ["Ref README.md"]` 等是无效内容，Speckit 无法消费。 |
| 正例 | 每个字段都有从设计文档中提取的具体值 |
| 反例 | `function: "TODO"`、`constraints: ["Kotlin + Views"]`（缺少性能/安全/车机约束）、`acceptance_criteria.items: ["Ref README.md"]` |
