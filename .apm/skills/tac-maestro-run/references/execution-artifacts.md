# Maestro Execution Validator 产物与 Bug 约定

## 执行链路

`tac-maestro-run` 是 LLM-B Execution Validator，负责在真实设备上执行已有 Maestro case/flow，收集产物，输出通过/失败结论，并在产品缺陷时生成 Bug。

推荐链路：

1. 通过 AL 或本地 adb 获取目标 `deviceId`。
2. 构建并安装 `app-debug.apk`。
3. 使用 Maestro MCP 做交互式选择器探测和短 flow 修正。
4. 使用 `tac_run_maestro_selftest.py` 做完整 CLI 闭环执行。
5. 保存 JUnit、截图/视频、commands、logcat。
6. 失败时按规则生成 `persistent-assets/governance/issues/BUG*.md`。

## MCP 与 CLI 分工

- MCP 适合调试：`list_devices`、`inspect_screen`、短 `run`、`take_screenshot`。
- CLI 脚本适合交付和 AL 调度：构建、安装、启动指定 Activity、清理数据、卸载目标包、保存 logcat、生成 Bug。
- 选择器修正必须引用 `inspect_screen` 输出作为依据。
- 选择器、等待时间、前置步骤可以修正；产品预期不能直接修改。

## 标准产物

| 产物 | 默认路径 | 用途 |
|------|----------|------|
| JUnit 报告 | `build/maestro-results/report.xml` | 主结果依据 |
| 截图/视频 | `build/maestro-results/` | 失败视觉证据 |
| Logcat | `build/maestro-results/logcat.txt` | 应用日志 |
| Bug 文档 | `persistent-assets/governance/issues/BUGyyyyMMddHHmmss.md` | 产品缺陷记录 |

通过判定：

- `report.xml` 存在。
- JUnit `failures="0"`。
- `.case.md` Execution Record 已写入设备、Git commit、结果和产物路径。

失败判定：

- Maestro 返回失败。
- JUnit 包含 `failure` 或 `error`。
- 必要屏幕状态无法到达。

## Bug 文档字段

产品缺陷时生成的 Bug 至少包含：

- Bug ID、发现时间、状态、优先级、来源。
- Flow、DeviceId、Git Commit、APK。
- 现象、预期行为、复现步骤。
- 日志位置、JUnit 报告路径、Maestro 产物目录。
- 影响范围。

## 第一阶段不做

- 不接入 Maestro Cloud。
- 不自动调用外部缺陷系统 API。
- 不做复杂根因归类。
- 不在 Maestro flow 内承担环境安装和 Bug 生成。
- 不一次性迁移所有人工测试路径。
