# Maestro Case Writer 工作流边界

## 角色定位

`tac-maestro-case` 是 LLM-A Case Writer，只负责读取需求、设计、quickstart 和代码资料，生成可追溯的 Test Case、Maestro flow 和覆盖矩阵。

## 输入范围

可按需读取：

- `specs/<feature>/spec.md`
- `specs/<feature>/quickstart.md`
- `specs/<feature>/plan.md`、`tasks.md`、`data-model.md`、`contracts/`
- `persistent-assets/design/_baseline/ui/*.md`
- `persistent-assets/design/_baseline/0[1-3]-*.md`
- 已有同类 Maestro flow
- 关键布局、Activity、ViewModel 或状态机代码

## 输出约定

- Case: `persistent-assets/automated-testing/_baseline/cases/<feature>/<case_id>.case.md`
- Flow: `persistent-assets/automated-testing/_baseline/flows/<case_id>.yaml`
- Coverage matrix: `persistent-assets/automated-testing/_baseline/cases/<feature>/coverage-matrix.md`

## 职责边界

- 每条用例必须追溯到 quickstart 路径、AC 编号、FR 编号或页面规则。
- 用例必须写明前置条件、环境假设、设备可变项和恢复策略。
- YAML 优先使用稳定 `id`；没有稳定 id 时，记录“需 MCP 现场修正”的风险。
- 本角色不执行设备测试，不连接 Maestro MCP，不使用 `inspect_screen`。
- 本角色不能根据屏幕现象修改需求预期。

## 与 Execution Validator 的交接

- `tac-maestro-run` 负责真实设备执行、选择器现场修正、报告收集和 Bug 生成。
- 执行中修正的选择器、等待时间、前置条件和设备差异需要回写到 Case/Flow，并记录依据。
- 产品预期和实现不一致时，由 Execution Validator 生成 Bug 或待确认项，不反向修改 Case Writer 的验收结论。

## Case Writer 产物闸门

- YAML 能被 Maestro 解析。
- 每条用例至少有一个明确来源。
- 每条 flow 都有 `name`、`tags`、`properties.sourceSpec`、`properties.path`。
- 高风险选择器必须有替代策略或 Known Risks 记录。
- Execution Record 留空，等待 `tac-maestro-run` 填写。
