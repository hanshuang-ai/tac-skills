---
name: "tac-experience-distill"
version: 0.4.5
description: "引导经验沉淀到正确载体（Issues/Memory/宪章），在 Feature 完成或踩坑后触发。所在环节：⑧ 经验沉淀。"
user-invocable: true
---

## Step 1: 回顾本次工作

列出本次工作中值得沉淀的内容：

1. **踩过的坑** — AI 犯了什么错？人工纠正了什么？
2. **有效的做法** — AI 做对了什么非显而易见的事？
3. **新发现的知识** — 发现了代码/文档里看不出来的背景？
4. **流程问题** — Speckit 流程、宪章、Skill 有什么不够用的地方？

如果以上都没有（大部分情况），直接结束，不需要强制沉淀。

## Step 2: 判断沉淀载体

对每一条值得沉淀的内容，按以下决策树选择载体：

```
这条经验属于什么类型？
│
├── 具体的 bug/问题/踩坑
│   → 写入 persistent-assets/governance/issues_and_learnings.md（ISSUE 格式）
│
├── AI 行为纠偏（"以后别再这样做"）
│   │
│   ├── 反复出现（第 3 次以上）
│   │   → 升级到宪章或专项规范
│   │
│   └── 首次出现
│       → 写入 Memory（feedback 类型）
│
├── 项目临时状态（"当前在做什么"，跨多人 + 持续 >1 天 + 可过期 ≤30 天）
│   → 调用 /tac-team-status 写入 persistent-assets/governance/team-status.md（团队级，跨工具可见）
│   注：仅对个人有用 → 写入工具私有 Memory（project 类型）
│
├── 规则/约束（"以后都必须这样做"）
│   → 升级到宪章或专项规范
│
└── 高频场景缺少 Skill/脚本
    → 创建新 Skill 或脚本
```

## Step 3: 按格式写入

### 写入 Issues（persistent-assets/governance/issues_and_learnings.md）

```markdown
## ISSUE-NNN: <简短标题>

### 现象
<什么操作导致什么结果>

### 根因
<为什么会出现这个问题>

### 修复
<如何修复的，附关键代码>

### 防范
<如何避免再次出现：检查清单/Skill 增强/规范补充>

### 追溯
- 关联 Feature: NNN-feature-name
- 关联宪章条款: <如果有>
```

### 写入 Memory

```markdown
---
name: <简短名称>
description: <一句话描述>
type: <feedback | project | reference>
review_after: <YYYY-MM-DD，建议 1-3 个月后>
---

<正文结论>

**Why:** <为什么要记住>
**How to apply:** <在什么场景下使用>
```

### 升级到宪章/专项规范

1. 确定应写入哪个专项规范文件
2. 在对应章节追加条款
3. 更新宪章的 Sync Impact Report
4. 通知团队

## Step 4: 评估是否需要新增 Skill/脚本

如果本次经验揭示了一个高频场景缺少自动化支持：

- 重复性流程 → 考虑新增 Skill
- 可自动检测的违规 → 考虑新增脚本 + Hook
- 记录到仓库根 `Android-AI编程工程实践指南.md` 附录的 Skill/脚本清单中

## Step 5: 清理过期团队状态

趁此机会扫描团队级临时状态：

```bash
# 路径相对于本 SKILL.md 所在目录（部署后位于 .claude/skills/<name>/ 等）

# 团队级临时状态（persistent-assets/governance/team-status.md）
bash scripts/tac-check-team-status-expiry.sh
```

如果有过期条目，决定：更新 / 延期 / 删除 / 升级到宪章。工具私有 Memory 由各 IDE 自管理，不在本节扫描范围。
