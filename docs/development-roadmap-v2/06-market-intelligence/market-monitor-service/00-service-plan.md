# market-monitor-service开发计划

## 目标

建立交易时段行情接入、5分钟Bar、Watchlist和确定性异常事件。领域基线见[盯盘服务设计](../../../architecture/services/market-monitor-worker.md)与[ADR-019](../../../architecture/adr/ADR-019-free-first-intraday-watchlist.md)。

## 内部阶段

1. [Gateway、Bar和Watchlist最小切片](./01-scaffold-bars-watchlist.md)。
2. [异常规则、River影子和强化](./02-core-integration-hardening.md)。
3. [测试](./90-test-plan.md)与[验收](./99-acceptance.md)。

market-monitor-agent只在阶段09接入；本服务无交易权限。

首版运行档固定为`FREE_TIERED_10_20_30`：每10分钟调用一次批准的批量行情Adapter，再本地过滤活跃Watchlist；P0持仓/待执行证券每10分钟评估，P1日频候选股每20分钟评估，P2人工关注股每30分钟评估，均复用同一批快照。默认50支，完成20个交易日稳定性验收后最多80支；100支只验证容量和受控降级。不得逐股请求，也不得把每个批次视为一次Agent或交易触发。

`MonitorPolicy`版本化间隔、阈值、冷却和升级/降级规则，并在交易时段冻结。阈值动作只允许HOLD、WATCH、DELAY、CANCEL、INTRADAY_RISK_REDUCTION和EXECUTION_CORRECTION；不得重新计算日频Alpha或以普通盘中波动生成新的组合调仓。
