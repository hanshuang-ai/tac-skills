# 拆分方法论核心（Methodology Core）

> 来源: SKILL.md §3
> 版本: v4.3
> 用途: 功能组级拆分 + 九字段原则详解 + 迭代标识批次区分 + 设计文档完整溯源

---

## 原则 1：功能组级拆分

拆分粒度以**功能组**为准。一个功能组 = 一个 Story，不再向下细分。

```
首页
 ├─ Banner              ← 功能组 = Story 1
 ├─ 应用推荐             ← 功能组 = Story 2
 └─ 应用分类             ← 功能组 = Story 3
```

---

## 原则 2：九字段全覆盖 + 完整溯源

每个 Story 字段与设计文档的对应关系：

| 字段 | 数据来源 | 参考表定位 |
|------|---------|-----------|
| 功能 | PRD | `prd` → §章节号 |
| 场景 | PRD + 交互稿 | `prd` §章节 + `interaction` §规则 |
| 输入 | 详设(DLD) | `dld` §接口 |
| 输出 | 交互稿 + 详设 | `dld` §响应 + `interaction` §规则 |
| 约束 | HLD + 非功能需求 | `hld` §架构 |
| 验收标准 | AC + 自测用例 | `ac` + `self_test` 用例编号 |
| 迭代标识 | SRS 版本号 | — |
| 日期 | 拆分当日 | — |
| 参考 | 全部设计文档 | 结构化表格 |

### 参考字段结构化溯源（v4.3）

参考表是"谁说了什么"的完整索引：

| 引用类型 | 键名 | 0-1必填 | 格式 | 示例 |
|----------|------|:---:|------|------|
| 需求规格 | `prd` | ✅ | 文档 + `§章节 章节名` | `SRS_V1.2.docx §2.3 Banner组件` |
| 业务领域 | `domain` | ✅ | 文档 + `§章节` | `领域设计.md §3 鉴权上下文` |
| 概要设计 | `hld` | ✅ | 文档 + `§章节` | `概要设计.md §6 Banner模块` |
| 详细设计 | `dld` | ✅ | 文档 + `§章节` | `详细设计.md §feature-banner` |
| 交互设计 | `interaction` | ✅ | 文档 + `§章节 + 规则编号` | `首页交互设计.md §3 RULE-HOME-001~010` |
| UI视觉 | `ui_assets` | ✅ | 文档 + 页面名+区域 | `应用商店UI设计概览.md 首页/Banner区` |
| 验收标准 | `ac` | ✅ | 文档 + 用例编号 | `验收标准.md TC-HOM-BNR-001` |
| 自测用例 | `self_test` | ✅ | 文档 + 用例编号 | `自测用例.md TC-HOM-BNR-001-S` |
| API文档 | `api` | ❌ | 文档 + `§接口名` | `API文档.md §/api/banner/list` |

1-N 场景：`domain`/`hld`/`dld`/`interaction`/`ui_assets` 仅增量部分必填，既有引用可省略。

纯后台 Story：`interaction`、`ui_assets` 显式标注 `（纯后台任务，无独立UI）`。

### 溯源链示例

```
RQ-HOM-BNR-01 Banner展示与轮播
 ├─ prd        → SRS_V1.2.docx §2.3 Banner组件
 ├─ domain     → 领域设计.md §3 推荐上下文
 ├─ hld        → 概要设计.md §6 Banner模块
 ├─ dld        → 详细设计.md §feature-banner
 ├─ interaction→ 首页交互设计.md §3 RULE-HOME-001~010
 ├─ ui_assets  → 应用商店UI设计概览.md 首页/Banner轮播区
 ├─ ac         → 验收标准.md TC-HOM-BNR-001
 ├─ self_test  → 自测用例.md TC-HOM-BNR-001-S
 └─ api        → API文档.md §/api/home/banner/list
```

## 原则 3~6

- **工程可独立实现**：单 Story 单职责
- **可测试**：验收标准可执行验证
- **可追踪**：每个字段 → 参考表中对应文档§章节
- **Spec 就绪**：全部 `spec_ready: true`

---

## 九字段完整示例

```markdown
# RQ-HOM-BNR-01 Banner展示与轮播

> 模块: 首页 | 功能组: Banner | 迭代标识: IT-V1.0

## 功能
进入首页时从服务端加载 Banner 列表，展示在顶部轮播区域。

## 场景
用户进入首页 → 自动请求 Banner → 顶部展示轮播。

## 输入
- 数据: Banner 列表（id, imageUrl, targetType, targetId, sortOrder）
- 来源: GET /api/home/banner/list

## 输出
- 结果: Banner 轮播 + 指示器
- 展示: 页面顶部图片 + 圆点指示器

## 约束
- 技术栈: Kotlin + ViewBinding，首屏 3 秒内，Android 10+

## 验收标准
- Given 网络正常 When 进入首页 Then 3秒内展示 Banner

## 迭代标识
IT-V1.0

## 日期
2026-06-02

## 参考
| 类型 | 来源 |
|------|------|
| 需求 | SRS_V1.2.docx §2.3 Banner组件 |
| 领域 | 领域设计.md §3 推荐上下文 |
| 概要设计 | 概要设计.md §6 Banner模块 |
| 详细设计 | 详细设计.md §feature-banner |
| 交互 | 首页交互设计.md §3 RULE-HOME-001~010 |
| UI | 应用商店UI设计概览.md 首页/Banner轮播区 |
| API | API文档.md §/api/home/banner/list |
| 验收 | 验收标准.md TC-HOM-BNR-001 |
| 自测 | 自测用例.md TC-HOM-BNR-001-S |
```
