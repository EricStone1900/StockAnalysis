# 12-02 Shadow Trading

## 实施步骤

1. Shadow记录“如果执行会怎样”，永不向Broker发送写命令。
2. 同时比较纯日频固定窗口、盘中延迟、一次风险减仓、最多两批、主策略、Challenger、人工实际操作和NO_REBALANCE基线。
3. 保存理论下单时间、可成交性、价格、费用、滑点、容量和后续Outcome。
4. 建立决策差异、漏交易、过度交易、风险拒绝有效性和人工覆盖效果报告。
5. Shadow结果进入阶段11时明确episodeType，不作为真实收益。
6. 单独报告第二批按INTRADAY_RISK_REDUCTION、EXECUTION_CORRECTION或其他候选reason带来的成本后增量收益、尾部风险和人工覆盖效果。
7. 对比相同日频目标在不同版本MonitorPolicy和阈值下的延迟、取消、风险减仓和执行修正结果；不得把普通盘中阈值解释为新的Alpha策略收益。

## 测试

- Broker写接口在Shadow身份下网络和权限双重拒绝。
- 主/候选/NO_TRADE样本不混合。
- 市场数据迟到时不使用未来价格模拟成交。
- 多策略相同标的保持各自独立账本。
- 未通过阶段10联合回放的第二批新Alpha候选只能作为Shadow，不得影响生产Proposal、预算或订单。
