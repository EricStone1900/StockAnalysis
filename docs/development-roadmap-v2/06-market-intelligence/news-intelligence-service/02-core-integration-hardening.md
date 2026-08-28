# News 06-02 去重、实体、Agent契约与强化

## 实施步骤

1. 实现精确Hash、规范URL、近似标题/正文和事件聚类去重。
2. 使用Security Master API进行公司、别名、产品、行业和证券代码实体关联。
3. 生成NewsEventCandidate，包含来源集合、候选股票、时间范围和证据引用。
4. 定义Agent分析请求与FinancialNewsEvent回写Schema；本阶段用Fake Analyzer。
5. 保存影响方向、强度、期限、置信度和evidenceIds，但不能把LLM推测改写成原始事实。
6. 实现来源故障、新鲜度、限流、许可变更和Artifact恢复。

## 测试

- 同一转载事件只生成一个Candidate。
- 公司简称冲突不会静默关联错误股票。
- Prompt注入正文不改变Fake Tool权限契约。
- 重复agentRunId回写幂等。
- 来源全部故障时显示STALE而非伪正常。

