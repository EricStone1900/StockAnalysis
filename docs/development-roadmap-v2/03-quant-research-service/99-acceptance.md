# quant-research-service验收

- [ ] 可从固定DataVersion重建因子、模型和回测。
- [ ] PIT、样本外和未来数据泄漏测试通过。
- [ ] DailyAnalysisSnapshot原子发布且包含持仓股。
- [ ] Strategy Registry和Plugin SDK v1通过契约测试。
- [ ] 四个初始策略和NO_REBALANCE通过。
- [ ] 第三方Runner安全与许可门禁通过。
- [ ] 只有ACTIVE因子、模型和策略进入生产快照。
- [ ] 失败、重复、恢复和Artifact Hash测试通过。
- [ ] 服务不拥有TradeProposal、Approval或Order。

验收后冻结DailyAnalysisSnapshot和DailyStrategySnapshot v1。

