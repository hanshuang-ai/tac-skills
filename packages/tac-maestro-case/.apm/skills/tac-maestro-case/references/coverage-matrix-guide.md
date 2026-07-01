# 覆盖矩阵编写指南

## 用途

覆盖矩阵记录需求 → 测试用例 → Maestro flow 的完整映射关系，用于：

1. 量化自动化覆盖率
2. 追踪未覆盖需求及原因
3. 评估新增 flow 的优先级

## 矩阵格式

路径：`persistent-assets/automated-testing/_baseline/cases/<feature>/coverage-matrix.md`

```markdown
# <Feature> Maestro 覆盖矩阵

> 生成时间：yyyy-MM-dd HH:mm
> 生成者：tac-maestro-case Skill

## 覆盖统计

- 总路径数：N
- 已覆盖：X（X/N = xx%）
- 未覆盖：Y

## 详细映射

| 需求来源 | 路径/AC | 优先级 | Case ID | Flow 路径 | 状态 | 未覆盖原因 |
|----------|---------|--------|---------|-----------|------|-----------|
| quickstart.md | Path A: <路径标题> | P1 | <case_id> | persistent-assets/automated-testing/_baseline/flows/<case_id>.yaml | 已生成 | — |
| quickstart.md | Path B: <路径标题> | P1 | — | — | 未覆盖 | 需要外部服务 mock |
| quickstart.md | Path C: <路径标题> | P2 | — | — | 未覆盖 | 待生成 |
| spec.md | AC-001 | P2 | — | — | 未覆盖 | 被 Path A 隐式覆盖 |
```

## 未覆盖原因分类

| 原因类型 | 说明 | 建议 |
|----------|------|------|
| 待生成 | 可自动化但尚未编写 | 安排下一批生成 |
| 需要外部服务 mock | 依赖网络/服务端状态 | 评估 mock 可行性 |
| 需要物理操作 | 如拔插 USB、切换网络 | 保留人工验证 |
| 被其他用例隐式覆盖 | 路径被包含在更大路径中 | 标注被覆盖的 Case ID |
| 设备/ROM 限制 | 特定设备才能复现 | 标注目标设备 |
