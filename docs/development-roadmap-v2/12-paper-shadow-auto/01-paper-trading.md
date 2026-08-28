# 12-01 Paper Trading

## 实施步骤

1. 实现PaperBrokerAdapter，模拟委托、部分成交、撤单、费用、滑点、涨跌停、停牌和交易时段。
2. Paper账户、订单、Fill和Portfolio使用独立环境与命名空间，不能写人工/生产账本。
3. 复用完整Proposal、RiskReview、RiskEvaluation和Approval链路；可配置Paper自动批准，但必须保留审计。
4. 每日将模拟成交与市场数据对照，记录模型假设误差。
5. 运行足够长周期，覆盖无交易、异常、数据中断和Regime切换。

## 测试

- 确定性成交模拟和随机种子。
- 不可成交、部分成交、费用、滑点和撤单。
- Paper Fill不能污染真实Portfolio。
- 重启和重复事件不重复成交。

