# quant-research-service测试计划

## 测试矩阵

- 因子：PIT、股票池、生存偏差、缺失、极值、中性化和可复现。
- 模型：时序切分、泄漏、随机种子、样本外和漂移。
- 回测：信号/成交时间、成本、滑点、停牌、涨跌停和最低费用。
- 快照：原子发布、失败保旧、重复任务、Hash和新鲜度。
- 策略：Plugin Contract、NO_REBALANCE、最低持有期、换手、容量和Ensemble。
- 安全：隔离Runner、SBOM、许可证、超时、OOM和恶意输出。
- 契约：OpenAPI、事件、Artifact引用和跨语言Schema。

关键Fixture必须覆盖牛市、震荡、下跌、极端波动、停牌和数据缺口。

