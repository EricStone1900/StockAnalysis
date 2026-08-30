# 阶段02：market-data-service

## 目标

独立交付A股市场数据事实服务，为后续量化、新闻、盯盘、Regime和组合估值提供稳定的Security、Calendar、PIT数据和DataVersion。

详细领域基线见[市场数据服务设计](../../architecture/services/market-data-service.md)。

## 顺序

1. [骨架与Security/Calendar最小切片](./01-scaffold-security-calendar.md)。
2. [标准化、PIT与数据质量](./02-normalization-pit-quality.md)。
3. [DataVersion、快照、API与事件](./03-versioned-snapshot-contracts.md)。
4. [生产强化与运维](./04-hardening-operations.md)。
5. [首版数据源与PIT补全策略](./05-v1-data-source-policy.md)。
6. [首次真实Release人工导入](./06-first-real-release-import.md)。
7. [测试](./90-test-plan.md)与[验收](./99-acceptance.md)。

## 边界

- 拥有Security、TradingCalendar、MarketBar、FinancialFact和DataVersion。
- 不计算因子、策略、持仓、异常、Regime或交易建议。
- 原始数据Adapter可替换，领域模型不能绑定特定供应商字段。

## 阶段门禁

任意历史交易日能够重建当时可见数据；数据质量FAIL阻止DataVersion发布；服务可以使用本地Fixture在无其他业务服务时完成基础验收。

Fixture闭环不等于真实数据源已完成。进入阶段03真实数据验收前，必须按[首版数据源策略](./05-v1-data-source-policy.md)接入固定的`investment_data` Release并补齐对账、来源证据和许可记录；价值、质量及财务修订类因子还受各自PIT数据门禁约束。
