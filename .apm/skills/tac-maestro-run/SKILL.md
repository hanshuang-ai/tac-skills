---
name: "tac-maestro-run"
version: 0.4.5
description: >
  LLM-B Execution Validator: 在真实设备上执行 Maestro flow，通过 MCP 探测修正选择器，
  通过 CLI 脚本执行完整闭环，收集产物，通过时更新 Execution Record，失败时自动生成 Bug 文档。
  触发：用户说'执行Maestro''跑自测''验证flow''跑E2E''Maestro自测''设备验证''跑测试用例'等。
  所在环节：测试执行与验证。
---

# Maestro Execution Validator Skill

本 Skill 实现 LLM-B 角色：在真实设备上执行已有的 Maestro 测试用例，收集产物，生成报告或 Bug。

## 硬性约束

1. **不改需求结论** —— 若发现产品预期和实现不一致，生成 Bug 或待确认项，不直接修改 Case Writer 的验收结论。
2. 只能修改执行层问题：选择器、等待时间、设备前置准备、脚本参数、产物路径。
3. 对选择器的每次修改必须引用 `inspect_screen` 输出作为依据。
4. 执行报告必须包含：设备 id、Maestro 版本、Git commit、命令、结果路径。
5. 调试、现场校准、LLM 自动修 flow 时，默认按 **单个 case/flow 一次脚本调用** 执行；只有用户明确要求套件回归或 CI 批量时，才把 flows 目录一次性交给脚本。
6. 中断或失败退出后必须检查后台进程，确认没有遗留的 `tac_run_maestro_selftest.py`、本次 result-dir、或本次 flow 相关 Maestro 执行进程。

## Step 1: 收集执行参数（不可跳过）

检查用户输入是否提供以下信息。**DeviceId + Flow 路径必须齐全才能进入 Step 2。**

| 字段 | 必填 | 说明 |
|------|------|------|
| DeviceId | 是 | adb 设备标识符 |
| Flow 路径 | 是 | `.yaml` 文件路径或整个 flows 目录 |
| Case 路径 | 否 | `.case.md` 路径，用于更新 Execution Record |
| ExecutionMode | 否 | `single`（默认，逐 case/flow 调脚本）或 `suite`（一次执行目录） |
| StartActivity | 否 | 非 launcher Activity 的启动命令 |
| ClearAppData | 否 | 是否清除应用数据 |
| UninstallPackage | 否 | 需要卸载的目标包名 |
| SkipBuild | 否 | 是否跳过 Gradle 构建 |
| SkipInstall | 否 | 是否跳过 APK 安装 |

参数推导规则：
- 用户给 `.case.md`：读取其中 `Flow path`，以该 case 为执行与记录单位。
- 用户给 case 目录：读取目录下所有 `.case.md` 的 `Flow path`，逐 case 执行；每个 case 使用独立 result-dir。
- 用户给单个 `.yaml`：以该 flow 为执行单位；若能从 case 目录反查 `.case.md`，执行后更新对应 Execution Record。
- 用户给 flows 目录：除非用户明确要求 `suite`，先列出将执行的 flow，并按单 flow 逐个调用脚本。
- 第一条 flow 可执行 build/install；后续 flow 默认追加 `--skip-build --skip-install` 复用已安装 APK。若指定了 `--clear-app-data` 或 `--uninstall-package`，每个 case 都独立执行对应前置动作。

**追问模板（缺失 DeviceId 或 Flow 路径时使用）：**

> 为了执行 Maestro 自测，请补充以下信息：
>
> 1. 设备 ID（通过 `adb devices` 获取）？
> 2. 要执行的 Flow 路径（如 `persistent-assets/automated-testing/_baseline/flows/install_demo_success.yaml`）？
> 3. 是否需要启动特定 Activity？是否需要清除数据或卸载目标包？

## Step 2: 环境检查

执行以下检查，全部通过后才进入 Step 3：

```bash
# 1. 设备连接
adb devices
# 确认目标 DeviceId 在列表中

# 2. Maestro CLI
maestro --version
# 确认 Maestro 已安装

# 3. Python 3 可用
python --version
# 确认 Python 3.10+

# 4. APK 可用性（除非 --skip-build + --skip-install）
# 确认 app/build/outputs/apk/debug/app-debug.apk 存在
```

若使用 Maestro MCP，优先调用 `list_devices` 确认设备可见。

## Step 3: MCP 探测与选择器修正（可选但推荐）

在正式执行前，使用 Maestro MCP 进行小步验证：

1. **`inspect_screen`** —— 获取当前屏幕 view hierarchy。
2. 对比 `.yaml` 中的选择器与实际 hierarchy：
   - 若 `id` 匹配：确认可用。
   - 若 `text` 匹配但有 `id` 可用：建议升级为 `id` 选择器。
   - 若选择器完全不匹配：修正并在 `.case.md` 的 Known Risks 中记录依据。
3. **`run`** —— 对修正后的关键步骤执行短 flow 验证。
4. **`take_screenshot`** —— 截取当前状态用于辅助判断。

修正规则：
- 每次修正必须记录 `inspect_screen` 的输出片段作为依据。
- 修正只限于选择器、等待时间、前置步骤，不改预期结果。
- 修正后的 `.yaml` 需要回写到文件。

## Step 4: CLI 全量执行

### 4.1 默认：逐 case/flow 执行

使用 `tac_run_maestro_selftest.py` 对每个 case/flow 单独执行完整测试。每次调用必须使用独立 result-dir，建议命名为 `build/maestro-results/<case-or-flow-name>`：

```bash
python tac-skills/tac-maestro-run/scripts/tac_run_maestro_selftest.py \
  --device-id <deviceId> \
  --flow-path <singleFlowPath> \
  --result-dir build/maestro-results/<case-or-flow-name> \
  [--start-activity <activity>] \
  [--clear-app-data] \
  [--uninstall-package <package>] \
  [--logcat-tags Tag1 Tag2 ...] \
  [--skip-build] \
  [--skip-install]
```

多 case 执行策略：

1. 第一条命令不加 `--skip-build --skip-install`，完成构建和安装。
2. 第二条起默认加 `--skip-build --skip-install`，减少重复耗时。
3. 每条 flow 结束后立即读取该 result-dir 的 `report.xml`，判定 PASS/FAIL 并更新对应 `.case.md`。
4. 若某条 case 失败，先按 Step 5 判断是否执行层问题；修正后只重跑该 case，不重跑整组。
5. 若用户中断，立即执行进程检查，停止本次脚本进程树，并复查无残留。

### 4.2 可选：套件目录一次执行

仅在用户明确要求套件回归、CI 批量、或需要验证跨 case 连续状态时，才把目录一次性交给脚本：

```bash
python tac-skills/tac-maestro-run/scripts/tac_run_maestro_selftest.py \
  --device-id <deviceId> \
  --flow-path <flowDirectory> \
  --result-dir build/maestro-results/<suite-name> \
  [--start-activity <activity>] \
  [--clear-app-data] \
  [--uninstall-package <package>] \
  [--logcat-tags Tag1 Tag2 ...]
```

套件模式要求额外检查：
- JUnit 中必须能映射到每个 flow/case 的结果；若不能，最终报告中标注结果粒度不足。
- 失败后若无法定位具体 case，改用逐 case/flow 模式复跑失败范围。
- 套件模式更容易出现状态污染，报告中必须说明是否清理数据、是否复用应用状态。

关注以下产物：

| 产物 | 路径 | 说明 |
|------|------|------|
| JUnit 报告 | `build/maestro-results/<case-or-flow-name>/report.xml` | 主要结果依据 |
| 截图/视频 | `build/maestro-results/<case-or-flow-name>/` | 失败时的视觉证据 |
| Logcat | `build/maestro-results/<case-or-flow-name>/logcat.txt` | 应用日志 |
| Maestro commands | `build/maestro-results/<case-or-flow-name>/` | 命令执行记录 |

## Step 5: 结果分析与产出

### 5.1 通过时

1. 更新 `.case.md` 的 Execution Record：

```markdown
| Time | Device | Git Commit | Result | Artifacts | Bug |
|------|--------|------------|--------|-----------|-----|
| 2026-05-12 17:00:00 | <deviceId> | <commit> | PASS | build/maestro-results/<case-or-flow-name>/ | — |
```

2. 向用户报告通过结果，包含：
   - 设备信息
   - Maestro 版本
   - 执行时长
   - 产物路径

### 5.2 失败时

1. 分析失败原因，区分：
   - **执行层问题**（选择器失效、超时不足、前置条件不满足）→ 修正后重试
   - **产品缺陷**（行为与预期不符）→ 生成 Bug

2. 产品缺陷时，确认 Bug 文档已由脚本自动生成在 `persistent-assets/governance/issues/BUG*.md`。
   若脚本未自动生成，手动调用：

```bash
python tac-skills/tac-maestro-run/scripts/tac_create_bug_from_maestro_result.py \
  --result-dir build/maestro-results/<case-or-flow-name> \
  --device-id <deviceId> \
  --flow-path <flowPath>
```

3. 更新 `.case.md` 的 Execution Record：

```markdown
| Time | Device | Git Commit | Result | Artifacts | Bug |
|------|--------|------------|--------|-----------|-----|
| 2026-05-12 17:00:00 | <deviceId> | <commit> | FAIL | build/maestro-results/<case-or-flow-name>/ | persistent-assets/governance/issues/BUG20260512170000.md |
```

### 5.3 重试策略

- 执行层问题修正后，最多重试 3 次。
- 3 次仍失败，记录为"不稳定用例"并在 Known Risks 中标注。
- 产品缺陷不重试，直接生成 Bug。
- 多 case 执行时，只重试失败的 case；已通过 case 不重复执行，除非失败原因表明共享前置状态被污染。

### 5.4 中断与后台进程清理

若用户中断、命令超时、或终端显示脚本仍在后台运行，必须执行清理检查：

```powershell
Get-CimInstance Win32_Process |
  Where-Object {
    $_.CommandLine -match 'tac_run_maestro_selftest|<case-or-flow-name>|<result-dir>'
  } |
  Select-Object ProcessId,ParentProcessId,Name,CommandLine
```

确认目标进程后，停止本次自测进程树，并再次执行查询确认无残留。只停止能明确关联到本次 case/flow/result-dir 的进程；Maestro MCP 服务进程不属于本次 CLI 自测时不要误杀。

## Step 6: 输出总结

最终向用户报告：

1. 执行的 Flow 列表和结果（PASS/FAIL）
2. 修正的选择器及依据
3. 生成的 Bug 文档路径（如有）
4. 产物路径清单
5. 不稳定用例列表和建议

## 参考文件

| 文件 | 用途 |
|------|------|
| `scripts/tac_run_maestro_selftest.py` | 主执行脚本（Python，跨平台） |
| `scripts/tac_create_bug_from_maestro_result.py` | Bug 生成脚本（Python，跨平台） |
| `prompts/execution-validator.prompt.md` | 执行验证 prompt |
| `references/device-setup.md` | 设备准备检查清单 |
| `references/execution-artifacts.md` | 执行产物与 Bug 字段约定 |
