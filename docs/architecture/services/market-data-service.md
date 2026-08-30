# market-data-service

## 1. 定位

系统统一的证券与行情数据入口，负责把不同供应商数据转换为稳定、可回放、带版本的标准数据。Qlib、盯盘、组合估值和回测均通过此边界获取数据。

初期推荐使用 Python + FastAPI，便于复用 A 股数据生态并与 Qlib 数据流水线协同；未来若实时行情吞吐成为瓶颈，可将流式接入 Worker 单独使用 TypeScript、Go 或其他技术实现。

从第一阶段起作为独立Docker微服务项目部署。它可以与量化服务共享同一MinIO集群和宿主PostgreSQL实例，但必须使用独立Database/User，并通过版本化API、事件或不可变Artifact交换数据。

## 2. 数据范围

- 证券主数据：代码、交易所、上市退市、简称、曾用名、行业。
- 日线行情：开高低收、成交量、成交额、复权因子。
- 盘中行情：至少支持 5 分钟级别或供应商推送数据。
- 指数和行业行情。
- 交易日历和交易时段。
- 停牌、ST、涨跌停和交易状态。
- 公司行动：分红、送转、拆并股和复权信息。
- 财务报表、估值和实际披露时间。

## 3. 内部架构

    Provider Adapters
      -> Raw Landing
      -> Schema Normalizer
      -> Security Mapper
      -> Data Quality Pipeline
      -> Point-in-Time Builder
      -> Version Publisher
      -> Query API / Snapshot API

Provider Adapter 屏蔽各数据源字段和代码差异。业务层禁止直接调用第三方 SDK。

### 3.1 首版数据源策略

正式版v1以`chenditc/investment_data`的固定Release作为A股日频Qlib主输入；BaoStock补充历史估值、交易状态和基础财务指标，AKShare用于财务与公告交叉校验，巨潮资讯保存公告及更正原文，Tushare Pro在具备合法Token和配额时提供结构化修订校验。详细优先级、PIT规则和待实现清单见[阶段02首版数据源策略](../../development-roadmap-v2/02-market-data-service/05-v1-data-source-policy.md)。

补充源只填补明确缺失，不得无记录覆盖主源。跨来源冲突进入版本化对账策略；任何修复、来源切换或Release升级均产生新DataVersion。每个来源必须登记许可、署名、再分发限制、配额与停用方式，开源采集代码的许可证不能替代底层数据授权。

## 4. 核心数据契约

每条记录必须包含：

- symbol 和 exchange。
- eventTime。
- availableAt。
- ingestedAt。
- source。
- sourceRecordId。
- dataVersion。
- qualityStatus。
- sourceReleaseTag或sourceVersion、rawArtifactUri、rawArtifactHash和licenseRef。
- 字段级provenance；发生跨来源补全时必须指出原始来源和对账策略版本。

财务数据的 availableAt 使用实际披露时间，不使用报告期结束时间，避免回测未来函数。修订采用追加记录，保存revision、revisionReason和supersedes；只有公告日期而没有时刻时，使用版本化的保守可用时间规则。

## 5. API

查询接口：

- GET /api/v1/securities/{symbol}
- GET /api/v1/securities/{symbol}/status
- GET /api/v1/calendars/{market}
- GET /api/v1/market/bars
- GET /api/v1/market/snapshots/{snapshotId}
- GET /api/v1/fundamentals/{symbol}
- GET /api/v1/corporate-actions/{symbol}
- GET /api/v1/data-versions/latest

内部任务：

- POST /internal/v1/jobs/sync-daily
- POST /internal/v1/jobs/sync-intraday
- POST /internal/v1/jobs/rebuild-adjustments
- POST /internal/v1/jobs/build-pit-snapshot
- GET /internal/v1/jobs/{runId}

## 6. 数据质量

至少检查：

- 主键重复。
- 时间倒序和未来时间。
- 价格为负或高低价关系错误。
- 成交量、成交额异常。
- 交易日缺失。
- 停牌与缺失行情的区分。
- 复权因子跳变。
- 证券代码映射冲突。
- 同一字段跨供应商差异。

质量结果分为 PASS、WARN、FAIL。FAIL 阻止生产快照发布；WARN 必须随版本记录。

## 7. 盘中异常检测协作

本服务负责标准行情、交易状态和数据版本；独立的[market-monitor-service](./market-monitor-worker.md)负责交易时段持续连接、1分钟/5分钟聚合、确定性规则和River在线异常评分。

[market-regime-service](./market-regime-service.md) 基于本服务的指数、全市场和行业数据计算趋势、宽度、波动与流动性状态。本服务不拥有MarketRegimeSnapshot。

盯盘Worker只有触发异常时才调用Agent，初始规则包括：

- 价格变化超过动态阈值。
- 成交量相对历史分位异常。
- 波动率急剧变化。
- 跌破止损或关键风险线。
- 涨跌停、停牌、复牌状态变化。
- 持仓股相对指数或行业显著偏离。

异常输出必须使用 [shared-contracts](./shared-contracts.md) 中的MarketAnomalyEvent。market-data-service不调用大模型，也不直接触发交易。

## 8. 存储

- 原始数据：S3/MinIO，不覆盖历史文件。
- 标准业务数据：PostgreSQL 或 TimescaleDB。
- 大规模历史数据：Parquet。
- Qlib 输入：由发布版本生成 Qlib Data Cache。
- 最新行情缓存：Redis，但数据库或供应商快照仍是事实来源。

## 9. 可靠性和合规

- 保存供应商、授权范围和使用限制元数据。
- 同一数据源连续失败时降级到备用源，但标记 sourceChange。
- 不允许在同一生产快照中无记录地混用不同口径。
- 数据补录产生新版本，不覆盖已被历史决策使用的版本。
- 所有交易规则参数按生效日期版本化，禁止长期硬编码。

## 10. 后续扩展

- 港股、美股、基金、期货和宏观数据。
- 多供应商自动对账和可信度评分。
- 实时流式行情和消息总线。
- 与market-monitor-service分片和回放基础设施协同。
- 独立 Feature Store。
- 自动数据漂移检测。
- 面向回放的历史快照查询。

## 11. 验收标准

- 任一历史日期可以重建当时可见的数据快照。
- 同一版本的相同请求产生一致结果。
- 数据源失败不会产生半成品生产快照。
- Qlib 和 Node 服务读取的是同一语义的数据版本。
