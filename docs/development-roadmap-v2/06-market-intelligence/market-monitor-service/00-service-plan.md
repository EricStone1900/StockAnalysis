# market-monitor-service开发计划

## 目标

建立交易时段行情接入、5分钟Bar、Watchlist和确定性异常事件。领域基线见[盯盘服务设计](../../../architecture/services/market-monitor-worker.md)。

## 内部阶段

1. [Gateway、Bar和Watchlist最小切片](./01-scaffold-bars-watchlist.md)。
2. [异常规则、River影子和强化](./02-core-integration-hardening.md)。
3. [测试](./90-test-plan.md)与[验收](./99-acceptance.md)。

market-monitor-agent只在阶段09接入；本服务无交易权限。

