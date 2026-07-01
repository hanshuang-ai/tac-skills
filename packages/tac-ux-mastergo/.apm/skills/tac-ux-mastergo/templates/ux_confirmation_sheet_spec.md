# UX Confirmation Sheet 生成规范

> 本规范定义 `ux_confirmation_sheet.xlsx` 的结构与生成规则。
> 脚本实现：`scripts/gen_confirmation_sheet.py`。

## 触发条件

当 handoff 的待确认项中存在 `blocking` 或 `pre-blocking` 项，且研发在一审中判定需外部角色（product / interaction / visual）确认时生成。

> ⚠️ 运行 `gen_confirmation_sheet.py` 之前，**必须**将研发一审中当场消解的项写回 handoff §15（更新 `阻塞级别` 为已确认状态）。脚本读取的是磁盘文件，不包含对话中的内存结论。

## 文件定位

```
{output-dir}/ux_confirmation_sheet.xlsx
```

- **不入 git**（二进制不可 diff，最终结论写入 handoff markdown）
- 可多次生成（编号追加，旧文件共存），也可由研发手动在 Excel 中增删行

## Sheet 结构

### Sheet 0「使用说明」

固定内容，分三个区块：

**元数据区**（供回放脚本自动定位）：

| 字段 | 值 |
|:--|:--|
| 关联索引文件 | `{output-dir}/ux_handoff_index.md` |
| 产出目录 | `{output-dir}` |
| 关联 Handoff 数量 | N |
| 生成时间 | YYYY-MM-DD HH:MM |

**角色分工速览**：

| 角色 | 待确认项数 | 其中 blocking |
|:--|:--|:--|
| 产品经理 | N | N |
| 交互设计师 | N | N |

**填写约定**：

- 所有项在同一 Sheet，按「确认角色」列筛选定位各自负责项
- 阻塞级别与填写优先级：
  - 深红 **pre-blocking** → **必填**，当前阶段阻塞，不确认无法启动
  - 浅红 **blocking** → **必填**，开发启动前必须确认
  - 浅黄 **non-blocking** → 选填，可按「可继续假设」先行推进
- 填写「确认结论」列：
  - 认同推荐选项 → 写「同推荐」或复制推荐选项
  - 有不同结论 → 自行描述
  - ⚠️ 留空 → 默认按「可继续假设」执行
- 同时填写「确认人」「确认日期」；如需改派，下拉切换「确认角色」
- **回放说明**：填完后发回给开发者，开发者放回原目录，对 AI 说「回放UX确认单」即可自动更新对应 handoff

### Sheet 1：待确认项（单一汇总表）

所有待确认项合并在同一 Sheet，按「确认角色」列筛选即可定位各自负责项。
确认角色列支持下拉改派，无需跨 Sheet 复制。

| 列 | 名称 | 类型 | 说明 |
|:--|:--|:--|:--|
| A | 编号 | 文本 | 与 handoff §15 待确认项编号一致 |
| B | 来源 Handoff | 文本 | 如 `ux_handoff_download_flow.md` |
| C | 文档标题 | 文本 | Handoff 文档一级标题（如"首页 UX 交互落地文档"） |
| D | 问题描述 | 文本 | 完整问题，含背景上下文 |
| E | 阻塞级别 | 下拉校验 | pre-blocking / blocking / non-blocking |
| F | 确认角色 | 下拉校验 | 产品经理 / 交互设计师 / 视觉设计师 / 开发者 / 宿主/平台 / 数据/接口 / 混合角色 |
| G | 推荐选项 | 文本 | AI 给出的可选方案 |
| H | 可继续假设 | 文本 | 未确认时的安全 fallback |
| I | 确认结论 | ⚠️ 空白供填写 | ① 认同推荐→写「同推荐」② 不同结论→自行描述 ③ 留空→默认按「可继续假设」 |
| J | 确认人 | ⚠️ 空白供填写 | 填写人姓名 |
| K | 确认日期 | ⚠️ 空白供填写 | YYYY-MM-DD |

## 格式要求

- 表头行：加粗 + 浅灰底色（E0E0E0）+ 自动换行 + 冻结首行
- 数据行底色：pre-blocking → 深红（FFCCCC）/ blocking → 浅红（FFE0E0）/ non-blocking → 浅黄（FFFACD）
- D 列「阻塞级别」：数据验证下拉列表 = `pre-blocking,blocking,non-blocking`
- 列宽：A/B/D/H/I 自适应，C/F/G 适当加宽（≥40 字符宽）
- 所有 Sheet 冻结首行

## 生命周期

| 阶段 | 状态 | 存储 | 操作 |
|:--|:--|:--|:--|
| 生成 | generated | output-dir, 不入 git | `gen_confirmation_sheet.py` 生成 |
| 审核 | reviewed | output-dir, 不入 git | 研发在 Excel 中删行/改角色/增行 |
| 外发 | in-flight | output-dir + 外发副本 | 通过 IM/邮件发送 PM/UX |
| 回放 | replayed | output-dir, 不入 git | `replay_confirmation.py` 读取，幂等 |
| 归档 | archived | 删除或移入 `_archived/` | 全回放后开发者手动操作 |

- 确认结论最终载体是 handoff §15 待确认项（markdown），xlsx 非真相源
- `replay_confirmation.py` 可多次执行，已确认项做三态对比（adopted / revised / unchanged）
- 新增待确认项时生成新 xlsx，旧 xlsx 可共存（编号不重叠）
- 全部回放后 xlsx 可安全删除；脚本不自动删文件
