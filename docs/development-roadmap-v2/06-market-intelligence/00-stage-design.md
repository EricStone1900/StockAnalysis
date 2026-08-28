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

