# 05-03 财经新闻Agent契约与事件发布

## 目标

先建立新闻分析Port、结构化输出和回写接口；阶段08再接入真实financial-news-agent和模型Provider。

## 实施步骤

### 1. 分析Port

```python
class NewsAnalysisPort(Protocol):
    async def analyze(self, candidate_id: str, correlation_id: str) -> FinancialNewsEvent: ...
```

本阶段实现`FakeNewsAnalysisAdapter`用于契约测试，以及HTTP回写端点：

```text
GET  /internal/v1/event-candidates/pending
POST /internal/v1/event-candidates/{candidateId}/analysis-result
```

### 2. 输出校验

```python
class FinancialNewsEvent(BaseModel):
    event_id: str
    candidate_id: str
    affected_symbols: list[AffectedSymbol]
    impact_direction: Literal["POSITIVE", "NEGATIVE", "NEUTRAL", "UNCERTAIN"]
    impact_magnitude: Literal["LOW", "MEDIUM", "HIGH"]
    impact_horizon: Literal["INTRADAY", "SHORT_TERM", "MEDIUM_TERM"]
    evidence_ids: list[str]
    confidence: float = Field(ge=0, le=1)
```

回写时校验candidate仍存在、evidenceId属于该候选且结果未过期。

### 3. 事件发布

HIGH且达到置信度阈值的结果通过Outbox发布`FinancialNewsEventPublished`。事件只带eventId和关键引用，不带全文。

### 4. 阶段08接入点

真实Agent从pending接口取候选，通过Tool读取证据并调用回写端点。新闻服务不保存模型密钥。

## 测试案例

1. 不存在的evidenceId回写失败。
2. 重复回写同一agentRunId保持幂等。
3. 候选更新后旧分析结果被拒绝或标记过期。
4. HIGH事件写Outbox，LOW事件只保存不触发决策。
5. Fake Adapter可完成服务端闭环。

## 完成条件

- 在无真实模型情况下完成契约和事件测试。
- 阶段08只需实现Agent Adapter，不修改新闻事实模型。
- FinancialNewsEvent是不可变、可追溯对象。
