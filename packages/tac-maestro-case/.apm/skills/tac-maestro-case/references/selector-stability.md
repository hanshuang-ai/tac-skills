# 选择器稳定性评级指南

## 等级定义

| 等级 | 选择器类型 | 稳定性 | 维护风险 | 适用场景 |
|------|-----------|--------|----------|----------|
| S1 | `android:id` / `com.xxx:id/xxx` | 高 | 低 | 首选，代码重构时随 id 变化 |
| S2 | `contentDescription` | 中-高 | 低-中 | 无障碍标签，推荐用于图标按钮 |
| S3 | 精确文本匹配（中文） | 中 | 中 | ROM/语言切换可能失效 |
| S4 | 模糊文本 / 正则文本 / 位置关系 / index | 低 | 高 | 最后手段，必须有风险标注 |

## 选择器选择规则

1. **优先使用 S1**：检查布局 XML 或代码中是否有 `android:id`。
2. **S1 不可用时尝试 S2**：检查是否有 `contentDescription`。
3. **S2 不可用时使用 S3**：精确匹配完整可见文本。
4. **S3 存在多义性或使用正则时降级 S4**：使用 `.*`、`|`、部分匹配语义、`below`/`above`/`leftOf`/`rightOf`、`index`、坐标或滚动后点击都属于 S4。

## 追溯来源规则

1. 文案断言必须追溯到真实来源文件：布局 XML、`strings.xml`、数据构造代码、adapter、resolver 或 ViewModel。
2. 如果文案来自状态绑定、adapter、resolver 或 ViewModel，必须引用具体代码文件；不能只引用 `strings.xml` 或宽泛页面说明。
3. 正则文本选择器中的每个候选文案都应能在 Test Data / Source Materials 中找到来源。

## S3/S4 风险标注模板

在 `.case.md` 的 Known Risks 表格中记录：

```markdown
| Risk | Mitigation |
|------|------------|
| Step 3 使用 S3 文本选择器"<按钮文案>"，页面可能有多个同名按钮 | 优先补充 android:id；备选使用 `below: "<邻近稳定文本>"` 定位 |
| Step 7 使用 S4 位置选择器，系统页面因 ROM 不同布局可能变化 | 需用目标设备 inspect_screen 验证；建议补充 contentDescription |
| Step 3 使用 S4 正则文本选择器".*(下载|打开|更新|安装|已安装).*"，页面可能存在多义性或文案变化 | 优先补充稳定 id；同时在 Test Data 中引用每个候选文案的代码或资源来源 |
```

## 代码中提取 id 的方法

1. 搜索布局 XML：`grep -r "android:id=" app/src/main/res/layout/`
2. 搜索代码中的 `findViewById` / `viewBinding`：定位关键控件 id。
3. 如无稳定 id，在 `.case.md` 中标注"需 MCP 现场修正"并建议开发者补充 id。
