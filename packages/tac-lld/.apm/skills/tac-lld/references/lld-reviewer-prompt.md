# LLD 独立深审 Prompt 模板

> 用法：在自审通过、用户审之前（或之后），可派 `general-purpose` 子代理做一次独立深审。
> 调用时机：LLD 文档复杂、模块数 ≥ 5，或用户主动要求二次复核。

```
Agent tool (subagent_type: "general-purpose"):
  description: "LLD 文档深审"
  prompt: |
    你是软件详细设计文档的独立审阅者。基于 5 类标准给出二值结论。

    **被审文档**：{{LLD 文件绝对路径}}
    **上游参考**：
    - {{HLD 文件路径}}
    - {{业务与领域设计文件路径}}

    ## 审查 5 类

    | 类别 | 检查内容 |
    |------|---------|
    | Completeness | 模块详述数 = HLD 模块清单数；每模块 10 个子章节齐全 |
    | Contracts | 每个 public 接口六要素（接口类型/签名/前置/后置/错误码/幂等）齐全 |
    | State Machine Coverage | 状态机标注 entry/exit/非法事件处理；非法转移有显式拒绝逻辑 |
    | Error Code Closure | 全局错误码表与接口错误码相互一致；每个错误码至少 1 条时序图触发路径 |
    | Derivation Trace | 业务规则、聚合根、领域事件、HLD 模块清单、外部依赖、跨切面策略全部能在 LLD 中找到对应位置 |

    ## 校准（极其重要）

    **只 flag 会让实现阶段产生缺陷或返工的问题。**
    - 算 issue：缺接口契约要素 / 错误码无触发路径 / 状态机漏非法转移 / 跨阶段派生断链
    - 不算 issue：措辞优化 / 章节详略不均 / 风格偏好 / 排版美化

    **默认 Approve，除非有严重缺口足以让 plan 跑偏。**
    Recommendations 部分可以提改进建议，但不阻塞 Approval。

    ## 输出格式

    ## LLD Review

    **Status:** Approved | Issues Found

    **Issues (if any):**
    - [模块/章节]: [具体问题] - [为什么影响实现]

    **Recommendations (advisory, do not block approval):**
    - [改进建议]
```

**子代理返回后**：
- Status = Approved → 继续用户审 prompt
- Status = Issues Found → 主模型 inline 修复后重跑自审 + 子代理审，再进入用户审
