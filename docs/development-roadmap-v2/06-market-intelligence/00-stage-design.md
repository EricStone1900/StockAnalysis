# 阶段06：市场情报基础服务

## 目标

依次独立完成新闻情报、交易时段异常监控和市场状态三个服务。先交付确定性数据处理与标准事件，阶段09再接真实Agent。

## 顺序

1. [news-intelligence-service](./news-intelligence-service/00-service-plan.md)。
2. [market-monitor-service](./market-monitor-service/00-service-plan.md)。
3. [market-regime-service](./market-regime-service/00-service-plan.md)。
4. [阶段集成](./04-stage-integration.md)。
5. [测试](./90-stage-test-plan.md)与[验收](./99-stage-acceptance.md)。

## 边界

- 新闻服务拥有NewsItem、Candidate和最终FinancialNewsEvent存储，但LLM分析暂用Fake结果。
- 盯盘服务拥有Watchlist、分钟Bar、RuleVersion和MarketAnomalyEvent，不拥有订单。
- Regime服务拥有RegimeDefinition和MarketRegimeSnapshot，不修改RiskPolicy。
- 三个服务只读market-data契约，不直接访问其数据库。
- 盯盘首版采用[ADR-019](../../architecture/adr/ADR-019-free-first-intraday-watchlist.md)的`FREE_TIERED_10_20_30`：批量快照每10分钟一次，P0/P1/P2分别每10/20/30分钟评估；默认50支、验收后最多80支、100支仅压力测试；免费源失败或行情陈旧时失败关闭，不生成伪正常结论。
- 盘中阈值只用于HOLD、WATCH、延迟/取消未执行批次、风险减仓或执行修正；不重新计算日频Alpha、不产生新的盘中Alpha调仓。
