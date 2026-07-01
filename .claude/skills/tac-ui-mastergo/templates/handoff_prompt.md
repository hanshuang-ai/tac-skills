# Mode B 交接 Prompt

## 工作目录

`<work_dir>`

## 请先读取这些文件

1. `handoff_facts.json` — 首要摘录索引与 summary_view，必须优先读取
2. `recursive_blueprint.json` — 结构分解与 bounds 细节
3. `user_decisions.json`（如存在）— 用户/脚本/工作流决策
4. `token_registry.json` — 颜色、字体、尺寸等 token
5. `structural_hints.json` — 列表/重复结构 metrics
6. `prompts/render_plan.md` — Mode B 编码前规划模板，用于生成 `<work_dir>/render_plan.md`
7. `<work_dir>/render_plan.md` — Mode B 生成后的执行简报
8. `references/02_asset_processing.md` 和 `prompts/layout_android_xml.md` — 仅在 Mode B 开始渲染时读取

## 必须遵守这些决策

- 已确认渲染范围: <引用 handoff_facts.json.confirmed_render_scope 及其 decision_ref；不得重新解释>
- 坐标策略: <引用 handoff_facts.json.coordinate_policy_refs；不得重新计算成不同结论>
- 模块包含/排除: <引用 handoff_facts.json.module_index 的 included/excluded 结论和 blueprint_ref>
- 用户/工作流决策: <引用 handoff_facts.json.decision_refs>
- 未解决项: <引用 handoff_facts.json.unresolved_refs，进入 TODO/placeholder，不要编造默认值>

## 用户可指导修改的点

- 可请求调整渲染范围、交互行为、动态数据绑定、图标/图片替换、文案校准。
- 若用户修改渲染范围或坐标相关结论，必须先回到 Mode A 更新 `user_decisions.json`、`recursive_blueprint.json` 和 `handoff_facts.json`，再继续 Mode B。

## Mode B 执行要求

- 以 `handoff_facts.json` 摘录索引为入口，跳转到其引用的源文件读取细节；禁止重新推翻 confirmed scope、coordinate policy、module inclusion/exclusion。
- 编码前先读取 `prompts/render_plan.md` 并生成 `<work_dir>/render_plan.md`，作为连续进入编码的执行计划。
- 生成 Android XML/资源前，先读取 `prompts/layout_android_xml.md`。
- 对动态区域生成 Adapter/Data Model；对未解析资产使用 placeholder 并记录。
- 完成后运行布局 lint/build/screenshot 检查。

## validate_handoff.py

Mode B 前必须确认 Mode A 交接已通过：

```bash
python tac-skills/tac-ui-mastergo/scripts/pipeline/validate_handoff.py <work_dir>
```
