# 页面 UI 规格说明书 (Page UI Specification)

> 可选文档: 仅当用户在 Mode A required handoff 通过校验后选择生成时，才创建本规格。
>
> 信息来源: 本规格必须从 `handoff_facts.json` 摘录索引生成；确认渲染范围、坐标归一化、模块取舍、关键 bounds、未解决项不得与 `handoff_facts.json` 及其引用源不一致。尽量引用 `artifact + json_pointer + node_id`，避免复制长表。若发现缺失，先补全 `handoff_facts.json`，再生成本文。

## 1. 文档基本信息 (Document Metadata)

- 项目/模块名称: <project_or_module_name>
- 设计稿来源: MasterGo 链接 [文件名](fileId) + 图层 [图层名](layerId)
- 设计基准尺寸: <width_px>x<height_px> px (对应 Android <width_dp>x<height_dp> dp)
- 生成时间: <generation_timestamp>
- 工具版本: tac-ui-mastergo v0.4.6+ (Mode A)

## 2. 页面 UI 概述 (Page UI Overview)

### 2.1 页面功能与业务场景
<简述该页面的业务背景、核心功能以及用户主要操作流>

### 2.2 页面核心架构 (ASCII 示意图)
```text
<用 ASCII 图表示主要空间关系，标出 Canvas 范围、被排除或保留的系统栏 (StatusBar/NavigationBar)、主内容区、列表/卡片/面板，并在重要区域标注 node id>
```

### 2.3 布局层级与边界规范
- 已确认渲染范围 (Confirmed Render Scope): <引用 handoff_facts.json.confirmed_render_scope 的 decision_ref、selected_module_refs、excluded_module_refs；这是后续位置推导依据>
- 系统栏排除 (System Chrome Exclusion): <引用 handoff_facts.json.coordinate_policy_refs.excluded_chrome_refs，说明排除哪些系统组件（如 StatusBar/NavigationBar），以及排除尺寸和原因>
- 坐标归一化偏移量 (Coordinate Normalization Offsets): <引用 handoff_facts.json.coordinate_policy_refs.normalization_ref；关键节点 raw/normalized bounds 只列短摘录并给出 key_bounds_refs>
- 动态与静态布局划分: <引用 handoff_facts.json.module_index 的 dynamic_ref/list_metrics_ref，说明哪些区域是 RecyclerView 动态卡片，哪些是静态固定布局>

## 3. UI 细节规范 (UI Details)

### 3.1 颜色系统 (Color Palette)
<从 handoff_facts.json.semantic_index.color_token_refs 引用页面关键颜色映射；详细值跳转 token_registry.json。不要直接读取 semantic_mapping.json>

| 颜色类别 | MasterGo 原始值 (Hex/RGB) | 建议设计 Token | 建议 Android 资源名 (colors.xml Name) | 使用场景与节点 ID |
| :--- | :--- | :--- | :--- | :--- |
| 背景色 | | | | |
| 文本色 | | | | |
| 边框线 | | | | |
| 品牌/主色 | | | | |
| 辅助/状态 | | | | |

### 3.2 字体与排版样式 (Typography & Text Styles)
<从 handoff_facts.json.semantic_index.typography_token_refs 引用主要文本样式；详细值跳转 token_registry.json>

| 代表节点 ID | 文字内容/占位文案 | 字体大小 (Font Size/sp) | 字重 (Font Weight) | 行高 (Line Height) | 建议 Android TextAppearance 命名 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| | | | | | |

### 3.3 间距、对齐边距与几何坐标 (Spacing, Margins & Bounds)
- 页面全局对齐边距 (Global Padding): <引用 handoff_facts.json.coordinate_policy_refs.key_bounds_refs 和 module_index.bounds_ref；只列必要短摘录，详细 bounds 跳转 recursive_blueprint.json>
- 组件间距规范 (Component Spacing): <引用 handoff_facts.json.module_index 的 list_metrics_ref/list_metrics_override 或 bounds_ref；只列关键间距短摘录>

| 节点 ID | 角色 | Raw Bounds (x,y,w,h) | Normalized Bounds (x,y,w,h) | 对齐/间距证据 |
| :--- | :--- | :--- | :--- | :--- |
| | | | | |

### 3.4 交互控件与语义映射 (Interactive Widgets & Semantics)
<从 handoff_facts.json.semantic_index.widget_refs 引用识别出的 WT 组件或系统原生控件；不要直接读取 semantic_mapping.json>

| 节点 ID | 组件名称 (Name) | 识别出的类名 (Widget Class) | 关键属性 / Variant | 适配建议 |
| :--- | :--- | :--- | :--- | :--- |
| | | | | |

### 3.5 资产与图切资源 (Assets & Drawables)
<从 handoff_facts.json.semantic_index.image_icon_refs 引用需要导出的图标与位图资产>

| 节点 ID | 资产名称/用途 | 资产类型 (Vector/Bitmap/9-Patch) | 导出格式建议 | 建议资源文件名 |
| :--- | :--- | :--- | :--- | :--- |
| | | | | |

### 3.6 圆角、描边与阴影 (Shapes, Borders & Shadows)
- 卡片圆角半径 (Corner Radius): <列出主要卡片的圆角值，如 8dp, 12dp>
- 描边粗细与颜色 (Border Stroke): <描边粗细 px/dp 及颜色值>
- 阴影效果 (Box Shadows): <模糊半径、偏移量及颜色，说明如何在 XML 中使用 cardElevation 或 custom shape 还原>

## 4. 多状态与交互逻辑说明 (States & Interaction Logic)

- 页面级多状态 (Page-level States): <说明是否包含 Loading、Empty、Error 等缺省状态及对应节点>
- 元素级多状态 (Element-level States): <关键按钮、列表项的 Normal/Pressed/Disabled 状态样式差异>
- 动态数据绑定区 (Data Binding Areas): <需进行动态数据填充的节点 ID 与文案占位>

## 5. 开发与验证指引 (Development & Verification Guide)

- 预计输出布局文件名: <建议的布局 XML 文件名，如 activity_app_detail.xml>
- 资源集成路径: <建议的 res 目录位置>
- 待确认设计遗留问题 (Pending Design Issues): <列出设计稿中模糊、不一致或存在冲突的问题>
- 验证指标与 Lint 规则: <页面实现后的 Lint 验证标准或对比度要求>
