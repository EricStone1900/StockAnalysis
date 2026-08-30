# quant-research-service

## 1. 定位

独立的Python生产量化限界上下文，使用Qlib承载已批准因子计算、模型训练、日频策略、信号评价、回测和每日分析快照。

本服务输出股票研究结果、策略候选组合和版本化快照，不输出最终交易指令。完整策略插件和第三方接入规范见[可扩展日频策略平台设计](./daily-strategy-extension-design.md)。

本服务与供应商无关，不直接调用`investment_data`、BaoStock、AKShare、巨潮资讯或Tushare。所有研究任务只消费`market-data-service`发布的DataVersion和不可变Qlib Artifact；输入必须能追溯到来源Release、原始Hash、质量报告和来源策略版本。

推荐技术栈：Python、FastAPI、Qlib、Pandas/Polars、Parquet、DuckDB、PostgreSQL、S3/MinIO。RD-Agent运行在独立的[research-automation-service](./research-automation-service.md)，不是本服务的生产依赖。

## 2. 双通道设计

### 候选准入通道

    research-automation-service提交PromotionRequest
      -> 校验候选Artifact签名、数据版本和实验清单
      -> 本服务独立复算、时序验证和回测
      -> 生产准入门禁
      -> CANDIDATE
      -> 人工或治理规则批准
      -> APPROVED / ACTIVE

任何外部研究工具的产物都不能自动进入生产评分；本服务是Factor/Model Registry和生产准入规则的唯一写入方。

### 生产通道

    数据版本就绪
      -> 加载 ACTIVE 因子集合
      -> 加载已发布模型
      -> 计算因子和预测
      -> 生成股票评分与排名
      -> 分析候选股和持仓股
      -> 质量校验
      -> 原子发布 DailyAnalysisSnapshot

生产通道每天运行一次，建议在收盘后且数据源明确就绪后执行。

价格动量、波动率和流动性因子可在首版日频主数据通过门禁后进入候选验证。价值因子需要历史估值口径与PIT可用时间；质量和财务修订类因子还需要公告时间及完整修订链。依赖数据未满足时因子只能为`DRAFT`或Fixture候选，不能进入`ACTIVE`集合。

## 3. 内部模块

    QuantApi
    JobManager
    QlibDataAdapter
    UniverseService
    FactorRegistry
    FactorPipeline
    FactorEvaluation
    ModelRegistry
    TrainingPipeline
    InferencePipeline
    BacktestPipeline
    StrategyRegistry
    StrategyPluginSDK
    StrategyRunner
    StrategyEvaluation
    StrategySnapshotPublisher
    StrategyEnsemble
    PromotionGate
    SnapshotPublisher
    ArtifactRepository

API 进程只负责接受任务和查询结果；计算由 Worker 执行。

外部策略默认由独立`strategy-plugin-runner`容器执行，不加载到生产API或Qlib主Worker进程。Runner属于本限界上下文，但使用无生产密钥的独立镜像、Service Account和资源限制。

## 4. 因子生命周期

状态：

    DRAFT
      -> EXPERIMENTING
      -> CANDIDATE
      -> VALIDATED
      -> APPROVED
      -> ACTIVE
      -> DEPRECATED

每个因子记录：

- factorId、version、category、direction。
- 描述、公式和实现代码摘要。
- requiredFields、lookback、frequency。
- 作者类型：human 或 rd-agent。
- train、validation、test 时间范围。
- IC、RankIC、ICIR、覆盖率和换手率。
- 相关性、衰减、分层收益、成本后收益。
- 审核状态和生产生效时间。

## 5. 准入门禁

候选因子至少经过：

1. 代码静态检查和单元测试。
2. 禁止未来数据和 Point-in-Time 检查。
3. 缺失率和覆盖率检查。
4. 极值与数值稳定性检查。
5. IC、RankIC和时间稳定性。
6. 分层收益和方向一致性。
7. 因子衰减和换手率。
8. 与现有 ACTIVE 因子相关性。
9. 样本外和 Walk-forward 验证。
10. 不同市场状态稳定性。
11. 计入交易成本的回测。
12. 人工批准或受控发布流程。

## 6. 股票分析快照

DailyAnalysisSnapshot 至少包含：

- snapshotId、runId、asOfDate、dataCutoffAt、publishedAt。
- status、isStale。
- universeVersion、factorSetVersion、modelVersion、dataVersion。
- selectedStocks 和 heldStocks。
- 每只股票的 score、rank、percentile、signal。
- 因子原始值、标准化值和贡献度。
- 风险标记和 evidenceIds。

量化信号使用 POSITIVE、NEUTRAL、NEGATIVE 或数值分数，不直接使用最终 BUY、SELL 指令。

### 6.1 日频策略快照

ACTIVE策略在每日量化快照发布后运行，输出`DailyStrategySnapshot`：

- strategyId、strategyVersion、parameterSetId和Plugin API版本。
- dataVersion、universeVersion、factorSetVersion、modelVersion和costModelVersion。
- `NO_REBALANCE`、`REBALANCE_CANDIDATE`或`RISK_REDUCTION`。
- currentWeights、targetWeights和proposedChanges。
- expectedTurnover、estimatedTransactionCost和estimatedSlippage。
- evaluationSummaryRef、reasonCodes、warnings和evidenceIds。

日频只表示每天评估；再平衡由版本化RebalancePolicy控制，允许长期`NO_REBALANCE`。第三方策略只生成候选权重，不能创建订单、批准建议或修改RiskPolicy。

## 7. API

读取接口：

- GET /api/v1/snapshots/latest
- GET /api/v1/snapshots/{asOfDate}
- GET /api/v1/stocks/{symbol}/analysis
- GET /api/v1/factors
- GET /api/v1/factors/{factorId}
- GET /api/v1/models/{modelId}
- GET /api/v1/backtests/{runId}
- GET /api/v1/runs/{runId}
- GET /api/v1/strategies
- GET /api/v1/strategies/{strategyId}/evaluations
- GET /api/v1/strategy-snapshots/latest
- GET /api/v1/strategy-snapshots/{snapshotId}

任务接口：

- POST /internal/v1/runs/daily-analysis
- POST /internal/v1/promotion-requests/{requestId}/validate
- POST /internal/v1/runs/model-training
- POST /internal/v1/runs/backtest
- POST /internal/v1/runs/daily-strategies
- POST /internal/v1/strategies/{strategyId}/versions
- POST /internal/v1/strategies/{strategyId}/versions/{version}/validate
- POST /internal/v1/strategies/{strategyId}/versions/{version}/approve
- POST /internal/v1/strategies/{strategyId}/versions/{version}/activate
- POST /internal/v1/factors/{factorId}/promote

长任务立即返回 202 和 runId，通过状态查询或完成回调通知 Temporal。

## 8. 原子发布

    RUNNING
      -> 写临时 Artifact
      -> 完整性与质量校验
      -> 写不可变 Snapshot
      -> 事务更新 latest 指针
      -> READY

失败时保留上一份 READY 快照并返回 isStale=true，不允许查询到正在写入的部分结果。

## 9. 存储

- PostgreSQL：实验、因子、模型、运行和快照元数据。
- Parquet：因子矩阵、数据集、预测、持仓和回测明细。
- S3/MinIO：模型文件、报告、日志和不可变 Artifact。
- Artifact Registry：第三方策略Manifest、锁文件、SBOM、签名和Runner镜像Digest。
- Qlib Data Cache：由 market-data-service 发布的数据版本生成。
- MLflow 可选：实验追踪，但不是业务状态唯一来源。

## 10. 自动研究服务隔离

- RD-Agent和生成代码只在`research-automation-service`的Sandbox运行。
- 本服务只读取不可变候选Artifact，并在自己的受控执行环境复验。
- 候选服务无权连接本服务数据库；提交只能经过版本化API和事件契约。
- 通过静态扫描、独立复算、质量门禁和人工审批后，才创建新的Registry版本。

## 11. 后续扩展

- 因子和模型联合演化。
- 新增兼容`strategy-plugin/v1`的自研、开源和第三方日频策略。
- 在结构化查询和回测稳定后增加确定性Strategy Ensemble。
- 多股票池、多市场和多基准。
- 多模型 Ensemble 与市场状态条件模型。
- 为 [market-regime-service](./market-regime-service.md) 提供状态定义、条件因子和风险策略的历史回测，不直接发布生产MarketRegimeSnapshot。
- 在线漂移检测和重训练建议。
- 将回测计算扩展到分布式任务。
- 增加研究 Notebook Gateway，但生产发布仍走准入流程。
- 为 Agent 提供更细粒度的因子证据和反事实分析。

## 12. 验收标准

- 每个交易日可生成一份不可变、版本完整的分析快照。
- 自动研究候选无法绕过独立复验和批准流程进入生产。
- 任一回测可由数据版本、代码版本和配置重新运行。
- 主系统只通过 API 契约接入，不依赖 Qlib内部文件格式。
- 新策略不修改Agent和Workflow代码即可完成登记、验证和Shadow运行。
- 第三方策略无数据库、外网、模型和交易权限，失败不影响其他ACTIVE策略。
- 只有ACTIVE策略快照能够进入Agent生产上下文。
