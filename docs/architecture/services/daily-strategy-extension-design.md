# 可扩展日频策略平台设计

- 文档版本：1.0
- 基线日期：2026-08-28
- 所属限界上下文：`quant-research-service`
- 当前目标：日频计算、低频调仓、人工审批与人工执行

## 1. 定位

本设计为系统增加版本化日频策略能力，并预留后续接入自研、开源和第三方策略的标准扩展点。

日频策略负责把因子、模型预测、行情、持仓和市场状态转换为确定性的候选目标组合或调仓建议；Agent读取策略快照进行解释、比较和质疑，但不能运行任意策略代码、修改策略参数或直接生成订单。

```text
Factor/Model Signal
  -> Daily Strategy
  -> StrategySignalSnapshot
  -> Agent Assessment
  -> Main Decision
  -> Risk Review
  -> Deterministic Hard Risk
  -> Human Approval
```

`DAILY`表示每天评估，不表示每天交易。策略必须单独声明再平衡规则，允许连续数周或数月返回`NO_REBALANCE`。

## 2. 架构决策

### 2.1 当前不新增独立微服务

Strategy Registry、回测、生产信号和策略准入属于量化研究限界上下文，第一阶段放入`quant-research-service`。

服务内部可以独立部署以下进程：

- `quant-api`：策略注册、查询、批准和任务入口。
- `quant-production-worker`：只运行ACTIVE且受信任的生产策略。
- `strategy-validation-worker`：执行回测、Walk-forward和门禁。
- `strategy-plugin-runner`：隔离运行第三方策略。

这些进程使用同一限界上下文和数据库所有权，但具有不同镜像、Service Account、网络权限和资源限制。未来插件执行负载或安全边界显著扩大时，再把`strategy-plugin-runner`拆成独立服务。

### 2.2 插件边界优先于框架边界

业务代码依赖`StrategyPlugin`稳定契约，不直接依赖Qlib具体类或第三方库：

```text
Application Service
  -> StrategyRunner Port
       -> BuiltinStrategyAdapter
       -> QlibStrategyAdapter
       -> IsolatedContainerStrategyAdapter
```

以后接入Zipline、Backtrader、vectorbt、自研库或第三方Docker策略时，只增加Adapter，不修改Agent、Temporal和治理状态机。

## 3. 策略类型

第一版预留以下Strategy Family：

```ts
type StrategyFamily =
  | 'NO_TRADE'
  | 'TOPK_RANKING'
  | 'MULTI_FACTOR'
  | 'MOMENTUM'
  | 'MEAN_REVERSION'
  | 'LOW_VOLATILITY'
  | 'ENHANCED_INDEX'
  | 'SECTOR_ROTATION'
  | 'REGIME_OVERLAY'
  | 'PORTFOLIO_OPTIMIZATION'
  | 'ENSEMBLE'
  | 'CUSTOM';
```

建议首批实现：

1. `NO_TRADE`：保持当前组合，作为所有策略必须比较的基准。
2. `LOW_TURNOVER_TOPK`：基于Qlib评分、保留区间、最低持有期和调仓阈值。
3. `MULTI_FACTOR_QUALITY`：价值、质量、动量、低波动和流动性约束。
4. `REGIME_OVERLAY`：根据市场状态调整风险预算，不负责自行选股。

短周期均值回归、高换手轮动和复杂优化不进入第一批ACTIVE列表。

## 4. DDD模型

### 4.1 StrategyDefinition Aggregate

```ts
interface StrategyDefinition {
  strategyId: string;
  name: string;
  family: StrategyFamily;
  description: string;
  ownerType: 'INTERNAL' | 'OPEN_SOURCE' | 'THIRD_PARTY';
  ownerName: string;
  supportedMarkets: string[];
  supportedFrequencies: Array<'DAILY'>;
  createdAt: string;
}
```

### 4.2 StrategyVersion Aggregate

```ts
interface StrategyVersion {
  strategyId: string;
  version: string;
  apiVersion: 'strategy-plugin/v1';

  manifestArtifactId: string;
  codeHash: string;
  imageDigest?: string;
  dependencyLockHash: string;

  parameterSchemaRef: string;
  defaultParameters: Record<string, unknown>;
  requiredDataFields: string[];
  requiredFactorIds: string[];
  requiredModelCapabilities: string[];

  signalFrequency: 'DAILY';
  rebalancePolicy: RebalancePolicy;
  status:
    | 'DRAFT'
    | 'CANDIDATE'
    | 'VALIDATING'
    | 'VALIDATED'
    | 'APPROVED'
    | 'ACTIVE'
    | 'SUSPENDED'
    | 'RETIRED';

  licenseReviewId?: string;
  securityReviewId?: string;
  approvedBy?: string;
  effectiveFrom?: string;
}
```

### 4.3 RebalancePolicy

```ts
interface RebalancePolicy {
  evaluationFrequency: 'DAILY';
  schedule?: 'DAILY' | 'WEEKLY' | 'MONTHLY';
  minimumHoldingDays: number;
  cooldownTradingDays: number;
  minimumSignalChange?: number;
  minimumRankImprovement?: number;
  maximumNamesChanged?: number;
  maximumExpectedTurnover?: number;
  allowEventTriggeredRebalance: boolean;
}
```

再平衡策略不能覆盖`portfolio-risk-service`的每日交易批次、仓位、暴露和回撤上限。

### 4.4 StrategyEvaluation

```ts
interface StrategyEvaluation {
  evaluationId: string;
  strategyId: string;
  strategyVersion: string;
  parameterSetId: string;

  dataVersion: string;
  universeVersion: string;
  factorSetVersion?: string;
  modelVersion?: string;
  costModelVersion: string;

  trainPeriod?: DateRange;
  validationPeriod: DateRange;
  outOfSamplePeriod: DateRange;
  walkForwardConfigRef: string;

  benchmarkId: string;
  metrics: StrategyMetrics;
  regimeMetrics: Record<string, StrategyMetrics>;
  gateResults: GateResult[];
  artifactRefs: string[];
  result: 'PASS' | 'FAIL' | 'REQUIRES_REVIEW';
  contentHash: string;
}
```

## 5. Strategy Plugin SDK

### 5.1 设计目标

- 框架无关：Qlib和第三方框架通过Adapter接入。
- 输入不可变：策略不能回写行情、因子或持仓事实。
- 输出受限：只允许输出信号、排名、目标权重和调仓候选。
- 可复现：相同输入、代码、参数和随机种子产生相同结果。
- 可审计：保存Manifest、Hash、依赖、许可、输入输出和运行日志。
- 可隔离：第三方策略默认运行在无生产密钥的容器。

### 5.2 插件接口

Python SDK建议定义：

```python
from typing import Protocol

class StrategyPlugin(Protocol):
    def metadata(self) -> "StrategyMetadata": ...
    def parameter_schema(self) -> dict: ...
    def validate_context(self, context: "StrategyContext") -> None: ...
    def generate(self, context: "StrategyContext") -> "StrategyResult": ...
```

禁止在接口中传递数据库Session、HTTP Client、NATS Client、券商Client或宿主文件路径。

### 5.3 StrategyContext

```python
class StrategyContext(BaseModel):
    api_version: Literal["strategy-plugin/v1"]
    run_id: str
    strategy_id: str
    strategy_version: str
    parameter_set_id: str

    market: str
    as_of: AwareDatetime
    decision_available_at: AwareDatetime

    data_version: str
    universe_version: str
    factor_set_version: str | None
    model_version: str | None
    portfolio_snapshot_id: str
    market_regime_snapshot_id: str | None

    input_artifacts: list[ImmutableArtifactRef]
    parameters: dict[str, Any]
    random_seed: int
```

插件只能读取`input_artifacts`列出的只读文件或SDK提供的受控数据视图。

### 5.4 StrategyResult

```python
class StrategyResult(BaseModel):
    run_id: str
    strategy_id: str
    strategy_version: str
    as_of: AwareDatetime

    rebalance_decision: Literal[
        "NO_REBALANCE",
        "REBALANCE_CANDIDATE",
        "RISK_REDUCTION",
    ]

    scores: list[InstrumentScore]
    target_weights: list[TargetWeight]
    proposed_changes: list[ProposedPositionChange]

    expected_turnover: Decimal
    estimated_transaction_cost: Decimal
    estimated_slippage: Decimal

    reason_codes: list[str]
    warnings: list[str]
    evidence_refs: list[EvidenceRef]
    output_artifacts: list[ImmutableArtifactRef]
```

StrategyResult不能包含：

- `Order`或券商请求。
- `APPROVED`状态。
- 规避RiskPolicy的字段。
- 任意SQL、脚本或下一步执行指令。

## 6. Strategy Plugin Manifest

每个插件必须提供`strategy-plugin.yaml`：

```yaml
apiVersion: strategy-plugin/v1
kind: DailyStrategyPlugin
metadata:
  id: com.example.low-turnover-topk
  name: Low Turnover TopK
  version: 1.2.0
  ownerType: THIRD_PARTY
  owner: Example Team
spec:
  runtime: python
  entrypoint: example_strategy.plugin:LowTurnoverTopK
  supportedMarkets: [CN_A]
  supportedFrequencies: [DAILY]
  deterministic: true
  networkAccess: none
  requiredDataFields: [close, volume, suspended, limit_status]
  requiredFactors: []
  parameterSchema: schemas/parameters.json
  outputSchema: strategy-result.v1.json
security:
  imageDigest: sha256:...
  codeHash: sha256:...
  dependencyLockHash: sha256:...
license:
  spdxId: Apache-2.0
  sourceUrl: https://example.invalid/repository
```

运行时只信任已登记记录中的Digest和Hash，不能仅凭可变镜像Tag运行。

## 7. 插件执行模式

### 7.1 TRUSTED_IN_PROCESS

只允许系统自研、经过代码审查和锁定依赖的简单策略。优点是性能好，缺点是故障和权限隔离弱。

### 7.2 ISOLATED_CONTAINER

开源和第三方策略的默认模式：

```text
strategy-validation-worker
  -> 创建一次性Runner容器
  -> 挂载只读Input Artifact
  -> 执行StrategyPlugin
  -> 校验StrategyResult Schema
  -> 保存Output Artifact
  -> 销毁容器
```

最低安全要求：

- 非root用户和只读根文件系统。
- 无Docker Socket和宿主目录挂载。
- 默认无外网；需要外部数据必须由market-data-service预先采集。
- 无模型、数据库、NATS和券商密钥。
- CPU、内存、磁盘、进程数和运行时间限制。
- 临时工作目录，任务结束清理。
- 依赖允许列表、SBOM、漏洞扫描和镜像签名。
- 输入和输出文件内容Hash校验。

第三方策略验证失败不能自动扩大资源或权限重试。

## 8. Qlib Adapter

第一版使用Qlib实现内置日频策略：

```text
Qlib prediction score
  -> QlibStrategyAdapter
  -> BaseStrategy / TopkDropoutStrategy / custom strategy
  -> normalized StrategyResult
```

Qlib对象不能直接暴露给Agent或跨服务DTO。Adapter必须统一：

- Security ID和交易所代码。
- Decimal、时区和交易日语义。
- 信号日与可成交日。
- 停牌、涨跌幅限制和不可交易状态。
- 最低交易单位、成本和滑点模型。
- 当前持仓和现金约束。

Qlib提供策略和日频回测基础，但示例参数不能直接作为生产参数。

## 9. 第三方策略接入流程

```text
提交Source/Package/Image
  -> 许可证和来源审核
  -> Manifest与Schema校验
  -> 依赖锁、SBOM和漏洞扫描
  -> Sandbox安全测试
  -> PIT和未来数据检查
  -> 基础正确性测试
  -> Walk-forward和样本外回测
  -> 成本、换手、容量和Regime测试
  -> Shadow运行
  -> 人工批准
  -> ACTIVE
```

第三方策略身份只能：

- 提交候选Artifact。
- 查询自己的验证运行。

不能：

- 自己批准或激活版本。
- 读取真实账户和完整订单。
- 修改生产因子、模型或RiskPolicy。
- 向Agent直接注入Prompt。
- 请求主系统安装未审核的动态依赖。

## 10. 许可证和供应链治理

每个外部策略登记：

- 源仓库、作者和版本Tag/Commit。
- SPDX许可证和许可证文件Hash。
- 是否允许商业使用、修改和再分发。
- 归属声明和NOTICE要求。
- 依赖许可证清单。
- SBOM、漏洞扫描报告和镜像签名。
- 内部批准人及使用范围。

许可证不兼容、来源不明、依赖无法锁定或存在未处理高危漏洞的策略只能处于`CANDIDATE`或`SUSPENDED`。

## 11. 准入和验证门禁

策略至少通过：

1. 参数和输出Schema。
2. 确定性与随机种子测试。
3. Point-in-Time和未来数据检查。
4. 股票池历史成分和退市样本检查。
5. 信号时间与成交时间检查。
6. 停牌、不可交易状态和价格限制处理。
7. 样本外、Walk-forward和多时间窗口验证。
8. 交易成本、滑点和最低费用。
9. 换手、容量和流动性。
10. 最大回撤和尾部风险。
11. 不同Market Regime稳定性。
12. 与现有ACTIVE策略的相关性和边际贡献。
13. 参数敏感度和过拟合检查。
14. Shadow运行。
15. 许可证、安全和人工批准。

任一硬门禁FAIL时不能ACTIVE。策略收益高不能覆盖安全、许可、PIT或风险门禁。

## 12. DailyStrategySnapshot

```ts
interface DailyStrategySnapshot {
  snapshotId: string;
  runId: string;
  strategyId: string;
  strategyVersion: string;
  parameterSetId: string;

  asOfDate: string;
  dataCutoffAt: string;
  publishedAt: string;
  validUntil: string;

  dataVersion: string;
  universeVersion: string;
  factorSetVersion?: string;
  modelVersion?: string;
  portfolioSnapshotId: string;
  marketRegimeSnapshotId?: string;
  costModelVersion: string;

  rebalanceDecision:
    | 'NO_REBALANCE'
    | 'REBALANCE_CANDIDATE'
    | 'RISK_REDUCTION';

  currentWeights: PositionWeight[];
  targetWeights: PositionWeight[];
  proposedChanges: ProposedPositionChange[];

  expectedTurnover: number;
  estimatedTransactionCost: string;
  estimatedSlippage: string;

  evaluationSummaryRef: string;
  reasonCodes: string[];
  warnings: string[];
  evidenceIds: string[];
  freshness: DataFreshness;
  contentHash: string;
}
```

发布遵循原子快照规则。策略失败时保留上一份READY快照并标记`isStale=true`，不能发布部分组合。

## 13. 多策略合并

Agent可以解释冲突，但正式合并必须由确定性`StrategyEnsemble`完成：

```text
ACTIVE Strategy Snapshots
  -> freshness and eligibility gate
  -> regime applicability gate
  -> deterministic weights
  -> correlation and concentration control
  -> turnover budget
  -> EnsembleStrategySnapshot
```

Ensemble权重必须来自版本化配置或优化器。主Agent无权临时修改策略权重。

至少保留`NO_TRADE`基准，并说明其他策略相对它的预期边际收益、风险和成本。

## 14. Agent接入边界

### stock-analysis-agent

读取股票在ACTIVE策略中的评分、入选状态、目标权重、变化原因和信号稳定性，生成解释；不运行策略代码。

### market-state-agent

解释当前Regime对策略适用性的影响；不能修改StrategyVersion、Ensemble权重或RiskPolicy。

### main-decision-agent

读取DailyStrategySnapshot或EnsembleStrategySnapshot，说明策略之间的共识和冲突。它可以输出TradeProposalDraft，但不能把CANDIDATE策略当成生产证据。

### risk-review-agent

检查主Agent是否忽略NO_TRADE基准、成本、回撤、策略失效环境、相关性和数据过期。

所有Agent只读取结构化快照和证据，不读取第三方策略源码、依赖包、完整日志或可执行内容。

## 15. API和事件

### 15.1 API

- `POST /internal/v1/strategies`：登记策略定义。
- `POST /internal/v1/strategies/{strategyId}/versions`：登记版本和Manifest。
- `POST /internal/v1/strategies/{strategyId}/versions/{version}/validate`。
- `POST /internal/v1/strategies/{strategyId}/versions/{version}/approve`。
- `POST /internal/v1/strategies/{strategyId}/versions/{version}/activate`。
- `POST /internal/v1/strategies/{strategyId}/versions/{version}/suspend`。
- `POST /internal/v1/runs/daily-strategies`。
- `GET /api/v1/strategy-snapshots/latest`。
- `GET /api/v1/strategy-snapshots/{snapshotId}`。
- `GET /api/v1/strategies/{strategyId}/evaluations`。

批准、激活、暂停接口只允许治理角色调用，并要求`expectedVersion`、`actorId`、`reason`和`Idempotency-Key`。

### 15.2 事件

- `stock.strategy.strategy-version.registered.v1`。
- `stock.strategy.strategy-validation.completed.v1`。
- `stock.strategy.strategy-version.activated.v1`。
- `stock.strategy.strategy-version.suspended.v1`。
- `stock.strategy.daily-strategy.published.v1`。
- `stock.strategy.ensemble-strategy.published.v1`。

事件使用quant-research-service Outbox。大型回测、权重列表和日志只传Artifact URI与Hash。

## 16. 推荐工程目录

```text
services/quant-research-service/
  src/quant_research/
    domain/strategy/
      entities.py
      value_objects.py
      events.py
      policies.py
    application/strategy/
      register_strategy.py
      validate_strategy.py
      activate_strategy.py
      run_daily_strategies.py
      build_ensemble.py
    ports/
      strategy_plugin.py
      strategy_runner.py
      strategy_repository.py
      artifact_repository.py
    adapters/strategy/
      builtin/
      qlib/
      isolated_container/
    adapters/events/
    adapters/persistence/
  strategy_sdk/
    context.py
    result.py
    manifest.py
    validation.py
  tests/
    strategy_contract/
    strategy_golden/
    strategy_security/
    strategy_replay/
  Dockerfile
  Dockerfile.strategy-runner
```

第三方插件保存在独立仓库或Artifact Registry中，不复制到主服务源码目录。

## 17. 测试要求

### 17.1 Plugin Contract Test

- Manifest、参数和输出Schema合法。
- 相同输入、参数、种子和镜像Digest结果一致。
- 输入Artifact只读。
- 输出权重总和、Decimal和股票标识合法。
- `NO_REBALANCE`不产生伪调仓列表。

### 17.2 安全测试

- 读取生产环境变量失败。
- 访问网络和其他服务数据库失败。
- 写宿主目录和输入目录失败。
- Fork Bomb、超时、OOM和磁盘耗尽被限制。
- 修改输出Schema、伪造证据和Hash不匹配被拒绝。

### 17.3 金融正确性测试

- 信号日之后才能成交。
- 停牌和不可交易股票不生成可执行变化。
- 成本后结果与无成本结果分开。
- 历史股票池不使用未来成分。
- StrategySnapshot不能引用未来数据。
- 调仓频率和最低持有期正确。

### 17.4 回归和兼容性测试

- Plugin SDK v1 Fixture对所有插件运行。
- 新quant-research版本不改变旧插件相同输入结果。
- SDK破坏性变更发布`strategy-plugin/v2`，v1在迁移期继续运行。
- 第三方插件失败不影响其他ACTIVE策略和每日量化快照。

## 18. 推荐实现顺序

### S0：策略基础契约

- StrategyDefinition、StrategyVersion、RebalancePolicy和DailyStrategySnapshot。
- StrategyRunner Port、Plugin SDK v1和Fake Strategy。
- Registry API、数据库迁移和事件Schema。

### S1：内置策略

- NO_TRADE。
- LOW_TURNOVER_TOPK。
- MULTI_FACTOR_QUALITY。
- REGIME_OVERLAY。
- 回测、成本和原子发布。

### S2：Agent接入

- stock-analysis-agent读取策略快照。
- main-decision-agent读取策略共识和冲突。
- risk-review-agent检查基准、成本和适用环境。
- Golden Fixture覆盖NO_REBALANCE和冲突策略。

### S3：第三方插件

- Manifest、IsolatedContainerStrategyAdapter和Runner镜像。
- 许可证、SBOM、签名和安全扫描。
- 第一个外部示例策略完成CANDIDATE到Shadow流程。

### S4：多策略和规模化

- StrategyEnsemble。
- 相关性、边际贡献和容量分析。
- Plugin SDK v2兼容性机制。
- 必要时将Runner拆成独立服务。

## 19. 验收标准

- 新增内置策略只需要实现StrategyPlugin和Manifest，不修改Agent或Workflow代码。
- 新增第三方策略只需要提供兼容插件或容器，不获得数据库和交易权限。
- 每个策略版本可由代码、参数、数据、成本模型和镜像Digest复现。
- 只有ACTIVE策略可以进入生产Agent上下文。
- 日频评估不会强制日频交易，`NO_REBALANCE`是正常结果。
- 第三方插件失败、超时或恶意行为不影响其他策略和领域服务。
- 策略不能创建Order、批准建议或覆盖RiskPolicy。
- StrategySnapshot可追溯回测、许可证、安全审核和全部输入版本。
- Plugin SDK破坏性升级具有并行兼容和迁移方案。
