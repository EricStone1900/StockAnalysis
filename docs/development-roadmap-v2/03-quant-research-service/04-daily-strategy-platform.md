# 03-04 日频策略Registry与Plugin SDK

## 实施步骤

1. 实现StrategyDefinition、StrategyVersion、RebalancePolicy、StrategyEvaluation和DailyStrategySnapshot。
2. 建立`strategy-plugin/v1`的Context、Result和Manifest Schema。
3. 先实现Fake Strategy和NO_TRADE，再实现LOW_TURNOVER_TOPK、多因子质量和Regime Overlay。
4. 内置策略可受信任进程运行；第三方/开源策略默认一次性隔离容器，无外网、数据库和生产Secret。
5. 建立回测、PIT、成本、换手、容量、Regime、Shadow、安全、许可和人工审批门禁。
6. 只有ACTIVE StrategyVersion发布生产快照；正式合并由版本化Ensemble完成，Agent无权改权重。

```python
class StrategyPlugin(Protocol):
    def validate_context(self, context: StrategyContext) -> None: ...
    def generate(self, context: StrategyContext) -> StrategyResult: ...
```

## 测试

- 日频运行允许返回NO_REBALANCE，不创建交易批次。
- CANDIDATE不能进入生产快照。
- 第三方插件网络、数据库、宿主写入和Secret访问失败并审计。
- 新插件无需修改Agent/Workflow契约。

