# 设备准备检查清单

## 执行前必须确认

| 序号 | 检查项 | 命令 | 预期结果 |
|------|--------|------|----------|
| 1 | adb 设备可见 | `adb devices` | 目标 DeviceId 出现在列表中，状态为 `device` |
| 2 | Maestro CLI 可用 | `maestro --version` | 返回版本号（如 `2.5.1`） |
| 3 | Gradle 构建可用 | `.\gradlew.bat :app:assembleDebug` | `BUILD SUCCESSFUL` |
| 4 | APK 文件存在 | 检查 `app\build\outputs\apk\debug\app-debug.apk` | 文件存在 |
| 5 | 设备允许安装未知来源 | 设备设置检查 | 已开启 |

## 可选检查

| 序号 | 检查项 | 命令 | 说明 |
|------|--------|------|------|
| 6 | 目标包是否已安装 | `adb -s <id> shell pm list packages \| findstr <pkg>` | 判断是否需要 `-UninstallPackage` |
| 7 | 应用数据是否需要清除 | — | 判断是否需要 `-ClearAppData` |
| 8 | 目标 Activity 是否可启动 | `adb -s <id> shell am start -n <activity>` | 判断是否需要 debug manifest 开放 |
| 9 | 网络连通性 | `adb -s <id> shell ping -c 1 <target-host>` | 网络类 flow 需要网络 |

## 常见问题

### Q: Maestro 提示 "No devices found"

- 确认 `adb devices` 能看到设备。
- 确认没有多个 adb server 实例冲突。
- 尝试 `adb kill-server && adb start-server`。

### Q: 安装 APK 报 `INSTALL_FAILED_UPDATE_INCOMPATIBLE`

- 先卸载旧版本：`adb -s <id> uninstall <packageName>`。
- 或使用脚本参数 `-ClearAppData`。

### Q: 系统安装界面选择器不匹配

- 不同 ROM 的系统安装弹窗按钮 id 和文案可能不同。
- 使用 Maestro MCP `inspect_screen` 获取实际 hierarchy。
- 常见 id：`android:id/button1`（确认）、`android:id/button2`（取消）。
