# market-regime-service

## 1. 定位

计算全市场和行业环境的确定性/统计服务，输出版本化MarketRegimeSnapshot。它回答“当前是风险偏好上升、中性、风险下降还是压力状态”，为选股解释、盯盘、组合风险和主决策提供统一市场背景。

market-state-agent只解释本服务快照，不直接从数千只股票原始行情推导状态。

推荐技术栈：Python、FastAPI、Pandas/Polars、Qlib、River、ruptures、PostgreSQL、Parquet、OpenTelemetry。HMM可作为研究模型，但不作为第一版生产核心。

## 2. 职责边界

负责：

- 计算指数趋势、市场宽度、波动、流动性和行业相对强弱。
- 运行可解释市场状态评分和状态机。
- 应用迟滞、最短持续时间和重大事件快速降级规则。
- 可选使用River识别在线漂移。
- 使用Qlib和ruptures研究、回测和验证状态定义。
- 发布日频和盘中MarketRegimeSnapshot。
- 记录状态版本、特征版本和模型版本。

不负责：

- 直接产生个股BUY、SELL或订单。
- 自动修改生产因子权重。
- 自动修改硬风控阈值。
- 替代market-monitor-service检测单股异常。
- 让大模型直接计算市场宽度和资金指标。

## 3. 内部架构

    market-data-service / market-monitor-service
      -> MarketFeatureLoader
      -> TrendCalculator
      -> BreadthCalculator
      -> VolatilityCalculator
      -> LiquidityCalculator
      -> IndustryStrengthCalculator
      -> RegimeScoreEngine
      -> RiverDriftDetector 可选
      -> RegimeStateMachine
      -> SnapshotValidator
      -> MarketRegimeSnapshotPublisher

研究通道：

    历史特征
      -> ruptures变化点研究
      -> Qlib条件回测
      -> 可选HMM/聚类基线
      -> 候选RegimeDefinition
      -> 验证和批准
      -> ACTIVE定义

生产通道只加载ACTIVE定义和已批准模型版本。

## 4. 输入数据

### 指数和风格

- 策略基准指数。
- 代表大盘、中盘、小盘和成长风格的指数。
- 主要行业指数。
- 指数收益、趋势、波动和回撤。

### 市场宽度

- 上涨、下跌和平盘股票数量。
- 上涨比例和收益率中位数。
- 阶段新高、新低数量。
- 位于20日、60日均线之上的股票比例。
- 涨停和跌停数量。
- 上涨和下跌行业数量。
- 横截面收益离散度。

### 波动

- 指数实现波动率。
- 日内波动率。
- 个股横截面波动。
- 行业收益离散度。
- 股票相关性和同步下跌比例。

### 资金和流动性

- 全市场成交额和历史分位。
- 换手率和成交额变化。
- 大小盘成交额占比。
- 行业成交额和资金流指标。
- 可获得且口径稳定时的ETF、融资等数据。

资金流字段必须保存供应商和口径，不能混合不同来源后当作同一指标。

## 5. 第一版状态识别

第一版采用可解释维度评分：

- trendScore。
- breadthScore。
- volatilityScore。
- liquidityScore。

输出状态：

- RISK_ON。
- NEUTRAL。
- RISK_OFF。
- STRESS。

行业状态：

- LEADING。
- IMPROVING。
- WEAKENING。
- LAGGING。

状态映射规则必须版本化。不得仅凭单一指数涨跌决定市场状态。

## 6. 状态稳定机制

为防止频繁切换：

- 一般状态变化需要连续多个窗口确认。
- 设置进入阈值和退出阈值，形成迟滞。
- 设置minimumDurationWindows。
- 数据质量WARN时降低confidence，FAIL时不发布新状态。
- 停牌面积、数据中断或极端波动等硬事件允许直接降级到RISK_OFF/STRESS。
- 从STRESS恢复需要更严格的连续确认。

每次转换保存previousRegime、transitionReason和触发特征。

## 7. MarketRegimeSnapshot

字段遵循 [shared-contracts](./shared-contracts.md)，至少包含：

- snapshotId、asOf、frequency、publishedAt。
- overallRegime、regimeConfidence、previousRegime。
- trend、breadth、volatility、liquidity维度分数。
- benchmarkStates和industryStates。
- changeDetected、transitionReason。
- dataVersion、featureVersion、regimeDefinitionVersion。
- riverModelVersion或researchModelVersion。
- freshness、qualitySummary、evidenceIds。

快照不可变，latest指针通过事务原子更新。

## 8. 更新频率

| 任务 | 建议频率 |
|---|---|
| 日频正式状态 | 每个交易日收盘后，数据就绪后计算 |
| 盘中状态 | 15～30分钟 |
| 行业状态 | 30分钟或日频 |
| 重大风险重算 | HIGH/CRITICAL市场级异常触发 |
| River更新 | 每个已完成特征窗口 |
| 定义/模型重训 | 每周、每月或漂移触发 |

Agent只在状态变化、重大风险事件或主决策运行时调用，不随每个计算窗口调用。

## 9. 与开源项目的分工

- AKShare或商业数据源：原型阶段的指数、行业和资金数据。
- vn.py：盘中指数、ETF和行业代理行情接入。
- Qlib：历史特征、条件回测和状态下因子表现验证。
- River：在线漂移和增量统计，第二阶段以影子模式加入。
- ruptures：离线变化点检测和历史状态分段，不直接作为实时触发器。
- hmmlearn：可选HMM研究基线；因维护和解释性限制，不作为不可替换的生产依赖。

所有第三方输出先转换为内部特征和版本化Artifact。

## 10. API

读取接口：

- GET /api/v1/regimes/latest
- GET /api/v1/regimes/{snapshotId}
- GET /api/v1/regimes/history
- GET /api/v1/regimes/industries/latest
- GET /api/v1/regime-definitions/{version}

内部任务：

- POST /internal/v1/runs/daily-regime
- POST /internal/v1/runs/intraday-regime
- POST /internal/v1/runs/regime-research
- POST /internal/v1/runs/regime-replay
- GET /internal/v1/runs/{runId}

状态变化通过Outbox发布MarketRegimeChanged事件，事件只携带snapshotId、previousRegime、currentRegime、confidence和correlationId。

## 11. 与其他服务协作

- market-data-service提供标准市场和行业数据。
- market-monitor-service提供盘中聚合特征和市场级异常引用。
- quant-research-service执行状态条件因子和组合回测，但不拥有生产MarketRegimeSnapshot。
- agent-runtime-service中的market-state-agent解释快照。
- portfolio-risk-service可以读取状态作为附加输入，但硬上限仍由RiskPolicy决定。
- decision-governance-service在状态显著变化时触发重新评估。

## 12. market-state-agent输出

Agent输入MarketRegimeSnapshot和当前组合上下文，输出MarketRegimeAssessment：

- interpretation。
- suggestedRiskBias：NORMAL、CONSERVATIVE、DEFENSIVE。
- allowNewPositions建议值。
- preferredIndustries、avoidedIndustries。
- portfolioImplications、risks、evidenceIds。
- validUntil、agentRunId。

这些字段是决策上下文，不是硬风控命令。

## 13. 存储和可观测性

- PostgreSQL：定义版本、快照索引、状态转换和运行记录。
- Parquet：历史特征矩阵、研究标签和回放数据。
- S3/MinIO：研究Artifact、模型和报告。
- Redis：最新窗口缓存，不作为快照事实来源。

Metrics至少包含计算延迟、数据新鲜度、状态持续时间、切换次数、维度分数、失败率和旧快照使用次数。

## 14. 测试与回放

- 历史牛市、熊市、震荡和极端波动区间回放。
- 数据缺失、指数停更和行业成分变化。
- 状态迟滞和最短持续时间。
- 状态切换频率和事后收益/风险统计。
- 不同状态下因子、组合和风险策略表现。
- River冷启动和漂移误报。
- 定义版本升级前后并行影子比较。

不能使用未来数据为当前状态特征或标签赋值。

## 15. 部署策略

从第一阶段起以独立Docker微服务部署；API与日频/盘中Worker可使用同一镜像的不同启动命令，并共享本服务自己的数据库，但不能并入quant-research-service：

    market-regime-api
    market-regime-worker
    market-regime-research-worker 可选

服务拆分后其他消费者仍通过相同API和MarketRegimeSnapshot契约接入。

## 16. 后续扩展

- 市场状态条件因子模型。
- 行业轮动和风格轮动状态机。
- 跨资产宏观与风险偏好特征。
- HMM、聚类和集成模型，但必须保留可解释维度分数。
- 动态风险预算建议，经回测和治理批准后接入风控策略。
- 多市场独立状态和跨市场传导分析。

## 17. 验收标准

- 市场状态由确定性/统计服务计算，不由LLM直接计算。
- 日频和盘中快照都能追溯到输入数据和定义版本。
- 状态不会因单个普通窗口在RISK_ON和RISK_OFF之间反复跳转。
- 数据FAIL时不发布伪正常状态。
- 新定义先经过历史回放和影子运行，再允许成为ACTIVE。
- market-state-agent无法修改状态、因子权重或硬风控规则。
