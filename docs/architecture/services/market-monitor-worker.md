# market-monitor-service（含market-monitor-worker）

本限界上下文从第一阶段起作为独立Docker微服务项目部署。文档文件名保留`market-monitor-worker.md`以兼容既有链接；项目目录和镜像统一命名为`market-monitor-service`，其中Worker承担持续行情处理，可选API进程提供Watchlist、状态与回放查询。

## 1. 定位

交易时段持续运行的独立部署 Worker，负责实时或准实时行情接入、1分钟/5分钟聚合、确定性异常检测和在线异常评分，并发布标准 MarketAnomalyEvent。

它属于 market-data 领域，但与查询 API 分开部署，避免持续行情连接、计算负载和数据源故障影响普通查询。

推荐技术栈：Python、vn.py、River、FastAPI健康端点、PostgreSQL/TimescaleDB、Redis、OpenTelemetry。

## 2. 职责边界

负责：

- 连接实时行情网关或轮询行情供应商。
- 将供应商 Tick、快照或分钟行情转换为统一 MarketDataEvent。
- 聚合 1 分钟和 5 分钟 Bar。
- 计算滚动量价、波动率和相对强弱特征。
- 执行确定性异常规则。
- 可选执行 River 在线异常和漂移检测。
- 对异常事件去重、冷却和分级。
- 通过 Outbox 或内部事件接口发布 MarketAnomalyEvent。
- 提供历史行情回放和规则评估能力。

不负责：

- 调用大模型解释异常。
- 直接生成 BUY、SELL 或订单。
- 修改持仓和风险规则。
- 取代 portfolio-risk-service 的止损与硬风控。
- 将每个 Tick 写入 Temporal Workflow History。

## 3. 内部架构

    vn.py Gateway / Vendor Adapter / Polling Adapter
      -> MarketDataNormalizer
      -> EventEngine
      -> BarAggregator 1m/5m
      -> FeatureCalculator
      -> DeterministicRuleEngine
      -> RiverAnomalyEngine 可选
      -> SeverityCombiner
      -> DedupAndCooldown
      -> AnomalyOutbox
      -> Temporal Signal / Agent Activity Trigger

## 4. 开源组件使用方式

### vn.py

建议复用：

- vnpy.event：进程内行情事件循环。
- 实际可用的 A 股行情 Gateway。
- data recorder：Tick或K线记录能力。
- REST/WebSocket基础组件。

系统内部不能直接传播 vn.py 类型，必须在 Adapter 边界转换为共享契约中的 MarketDataEvent 和 MarketBar。

### River

建议用于第二阶段增强：

- 在线异常分数。
- 在线统计和增量标准化。
- 波动状态与数据分布漂移检测。
- 股票与行业关系变化检测。

River分数只参与异常等级计算，不控制止损、仓位或订单。

## 5. 行情接入模式

### 推送模式

供应商支持 WebSocket 或券商 Gateway 时持续接收数据，本地按窗口聚合。5分钟指的是输出和检测窗口，不代表每5分钟重连一次数据源。

### 轮询模式

供应商只支持 REST 时，在交易日历允许的时段每5分钟轮询持仓股、待执行股票和候选股票。请求必须批量化、限流并记录数据延迟。

两种模式输出相同内部契约，上游数据源可以替换。

### 免费首版运行档

`FREE_TIERED_10_20_30`遵循[ADR-019](../adr/ADR-019-free-first-intraday-watchlist.md)：每10分钟以一次批量快照覆盖活跃Watchlist，再在本地筛选和聚合；不得把50～100支股票拆成逐股请求。P0每10分钟、P1每20分钟、P2每30分钟评估，三层复用同一批快照且不额外请求上游。默认50支，完成稳定性验证后最多80支，100支仅用于压力测试。

免费数据源只适用于研究和Shadow的`best effort`准实时监控。计划窗口后120秒未完成、`quoteAgeSeconds`超过180秒、覆盖不足、字段异常或连续两轮失败时，必须标记`WARN/FAIL`、告警并停止产生“正常”事件或下游风险放行。P0的1～5分钟能力须等待经验证的推送、付费或券商只读Gateway，不能由免费逐股轮询替代。

## 6. 监控股票分层

| 等级 | 范围 | 建议频率 |
|---|---|---|
| P0 | 当前持仓、待执行指令 | 10分钟 |
| P1 | 当日量化候选股 | 20分钟 |
| P2 | 人工关注列表 | 30分钟 |
| P3 | 全市场 | 日频或使用供应商异常榜单 |

监控集合由 portfolio-risk-service、quant-research-service 和人工关注列表共同生成，保存 watchlistVersion。

首版默认把P0、P1和P2合并为不超过50支的活跃集合并使用10分钟批量采样、10/20/30分钟分层评估；通过ADR-019的80支门槛后才允许扩容。`MonitorPolicy`必须版本化间隔、阈值、冷却和升级规则，交易时段内冻结；阈值只能触发HOLD、WATCH、DELAY、CANCEL、风险减仓或执行修正，不能重新计算日频Alpha或创建新的盘中Alpha调仓。

### MonitorPolicy

```ts
interface MonitorPolicy {
  policyVersion: string;
  effectiveFrom: string;
  sampleIntervalMinutes: 10;
  tiers: {
    P0: { evaluationIntervalMinutes: 10; thresholdSetId: string };
    P1: { evaluationIntervalMinutes: 20; thresholdSetId: string };
    P2: { evaluationIntervalMinutes: 30; thresholdSetId: string };
  };
  cooldownMinutes: number;
  escalationRules: Array<{
    thresholdId: string;
    fromTier: 'P1' | 'P2';
    toTier: 'P0' | 'P1';
    expiresAt: string;
  }>;
  allowedActions: Array<
    'HOLD' | 'WATCH' | 'DELAY' | 'CANCEL'
    | 'INTRADAY_RISK_REDUCTION' | 'EXECUTION_CORRECTION'
  >;
}
```

首版只允许10/20/30分钟枚举，不开放任意分钟值。阈值升级可临时提高某证券的评估层级，但不改变日频目标组合，不增加上游批量请求，也不绕过每日0～2个组合调仓批次上限。策略变更默认下一个交易时段生效；紧急安全变更必须保存审批、原因和生效时间。

## 7. 特征计算

第一版至少计算：

- return1m、return5m、intradayReturn。
- volumeRatio、amountRatio。
- rollingVolatility。
- priceToVwapDeviation。
- benchmarkRelativeReturn。
- industryRelativeReturn。
- drawdownFromIntradayHigh。
- distanceToStopLoss。
- limitStatus、tradingStatus。
- quoteAgeSeconds 和 dataGapCount。

滚动窗口只使用事件时间不晚于当前窗口结束时间的数据。

## 8. 确定性规则

建议初始规则：

- PRICE_DROP、PRICE_SURGE。
- VOLUME_SPIKE、AMOUNT_SPIKE。
- VOLATILITY_SPIKE。
- RELATIVE_WEAKNESS、RELATIVE_STRENGTH。
- STOP_LOSS_APPROACHING、STOP_LOSS_TRIGGERED。
- TRADING_STATUS_CHANGE。
- LIMIT_STATUS_CHANGE。
- DATA_INTERRUPTION、STALE_QUOTE。

每条规则具有 ruleId、version、适用市场、阈值来源、有效期和严重级别映射。阈值应结合固定上限、股票历史分位、流动性和市场状态，避免所有股票使用同一百分比。

## 9. 综合分级

优先级顺序：

1. 硬事件直接决定最低严重等级，例如止损触发、停牌和数据中断。
2. 确定性规则生成 ruleScore。
3. River生成 onlineAnomalyScore 和 driftState。
4. SeverityCombiner结合是否持仓、仓位大小、[market-regime-service](./market-regime-service.md) 最新状态和冷却策略。

输出 LOW、MEDIUM、HIGH、CRITICAL。默认只有 MEDIUM 以上进入事件流水，HIGH/CRITICAL立即触发后续工作流。

## 10. MarketAnomalyEvent

字段遵循 [shared-contracts](./shared-contracts.md)，至少包含：

- eventId、eventVersion、symbol、detectedAt、windowStart、windowEnd。
- type、severity、ruleHits。
- observedFeatures、benchmarkContext。
- portfolioContextRef、marketDataVersion、watchlistVersion。
- dataFreshness、evidenceIds。
- detectorVersion、riverModelVersion。

事件以 eventId 幂等。相同股票、异常类型和窗口的重复消息不能重复触发Agent。

## 11. 与Temporal和Agent的边界

    market-monitor-worker
      -> 发布 HIGH/CRITICAL MarketAnomalyEvent
      -> Temporal 接收轻量事件或事件引用
      -> 调用 market-monitor-agent
      -> Agent读取完整事件、新闻、量化和持仓上下文
      -> 输出 IGNORE、WATCH、REASSESS 或 RISK_ESCALATION
      -> 必要时启动 InvestmentDecisionWorkflow

Temporal只保存 eventId、symbol、severity和必要引用，不保存Tick流和完整分钟序列。

## 12. 运行与健康检查

Worker至少暴露：

- GET /health/live
- GET /health/ready
- GET /internal/v1/monitor/status
- POST /internal/v1/monitor/reload-watchlist
- POST /internal/v1/replay-runs
- GET /internal/v1/replay-runs/{runId}

Readiness检查行情连接、交易日历、规则版本、watchlist和Outbox。行情源断开时服务仍可存活，但必须Not Ready并告警。

## 13. 存储和状态

- PostgreSQL：规则版本、watchlist、异常事件、Outbox和运行状态。
- TimescaleDB或Parquet：分钟Bar和回放数据。
- Redis：短期窗口、去重键和冷却状态。
- River模型状态：版本化快照到对象存储，并记录训练截止时间。

Redis丢失不能造成硬风险事件遗漏；关键窗口和事件需有可恢复来源。

## 14. 回放与测试

上线规则前必须使用历史分钟数据回放：

- 事件时间顺序和乱序数据处理。
- 停牌、复牌、涨跌停和午间休市。
- 数据中断和延迟。
- 规则触发次数、重复率和假阳性。
- 触发后主 Agent是否产生无意义的频繁决策。
- River冷启动、漂移和模型状态恢复。

回放使用和生产相同的 RuleEngine、SeverityCombiner 和事件契约。

## 15. 部署和扩容

初期一个 Worker覆盖全部监控股票。扩大后可按 symbol hash、市场或组合分片，每只股票在同一时间只能由一个活跃分片处理。

部署单元：

    market-data-api
    market-monitor-worker
    market-monitor-replay-worker 可选

使用 Leader Election 或分区所有权避免多副本重复处理。Outbox发布保证至少一次，消费者依靠eventId幂等。

## 16. 安全与数据授权

- vn.py及其他开源框架只提供连接和事件能力，不代表附带实时行情授权。
- Worker优先使用只读行情凭据，不配置下单权限。
- 即使Gateway同时支持交易，本进程也不得注册或暴露下单命令。
- Worker不持有模型密钥、审批权限和券商交易密钥。
- 数据源、授权范围、可保存字段和留存时间记录到Provider配置。
- 外部行情字段先通过Schema和数值校验，再进入规则引擎。

## 17. 后续扩展

- 接入更多vn.py Gateway和商业行情源。
- 实时Tick级别监控，但不改变Agent事件驱动原则。
- 增加在线变点检测和市场状态条件模型。
- 增加组合级、行业级和相关性异常事件。
- 增加影子规则，对比新旧规则但不触发生产决策。
- 阶段10将监控事件纳入日频目标组合、调仓预算、A股执行约束和成本后的联合回放；阶段12继续进行Paper/Shadow对照。

## 18. 验收标准

- 没有异常时不会调用大模型。
- 同一事件重复到达不会重复触发决策。
- 行情源断开、数据过期和窗口缺失均能被检测。
- Worker重启后可以恢复watchlist、规则版本、冷却和River模型状态。
- 历史回放与生产使用相同检测逻辑。
