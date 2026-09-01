# 02-04 可扩展日频策略、Plugin SDK和第三方接入

## 目标

在`quant-research-service`中实现版本化Strategy Registry、稳定Plugin SDK、首批低频日频策略、每日策略快照和第三方策略隔离执行基础。

完成后，新增兼容策略不需要修改Agent、Temporal Workflow、决策治理或执行服务。

## 前置条件

- 02-01 Factor Registry和股票池版本已经完成。
- 02-02成本后回测、样本外和Walk-forward已经完成。
- 02-03 DailyAnalysisSnapshot可以原子发布。
- 已阅读[可扩展日频策略平台设计](../../architecture/services/daily-strategy-extension-design.md)。

## 开发边界

负责：Strategy Registry、Plugin SDK、回测准入、策略运行、目标组合候选和策略快照。

不负责：最终TradeProposal、硬风控、审批、OrderIntent、券商执行和持仓入账。

## 实施步骤

### 1. 建立领域对象

在`src/quant_research/domain/strategy/`建立：

```python
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from pydantic import BaseModel, ConfigDict

class StrategyStatus(StrEnum):
    DRAFT = "DRAFT"
    CANDIDATE = "CANDIDATE"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    RETIRED = "RETIRED"

class RebalanceDecision(StrEnum):
    NO_REBALANCE = "NO_REBALANCE"
    REBALANCE_CANDIDATE = "REBALANCE_CANDIDATE"
    RISK_REDUCTION = "RISK_REDUCTION"

class RebalancePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    evaluation_frequency: str = "DAILY"
    schedule: str | None = None
    minimum_holding_days: int
    cooldown_trading_days: int
    minimum_signal_change: Decimal | None = None
    minimum_rank_improvement: int | None = None
    maximum_names_changed: int | None = None
    maximum_expected_turnover: Decimal
```

领域层不能导入Qlib、Docker SDK、FastAPI、NATS或数据库驱动。

状态转换只能通过Aggregate命令执行：

```text
DRAFT -> CANDIDATE -> VALIDATING -> VALIDATED
VALIDATED -> APPROVED -> ACTIVE
ACTIVE -> SUSPENDED -> ACTIVE
ACTIVE/SUSPENDED -> RETIRED
```

禁止`CANDIDATE -> ACTIVE`跳跃。

### 2. 建立数据库迁移

至少创建：

```text
strategy_definitions
strategy_versions
strategy_parameter_sets
strategy_evaluations
strategy_gate_results
strategy_plugin_manifests
strategy_runs
daily_strategy_snapshots
daily_strategy_snapshot_items
strategy_license_reviews
strategy_security_reviews
outbox_events
```

关键唯一键：

```text
(strategy_id, version)
(strategy_id, version, parameter_set_id, data_version, as_of_date)
(snapshot_id, symbol, exchange)
```

`code_hash`、`image_digest`、`dependency_lock_hash`和`manifest_hash`不能为空。内置策略没有独立镜像时，`image_digest`可以为空，但必须记录服务镜像Digest。

### 3. 实现Plugin SDK v1

建立`strategy_sdk/`：

```python
class StrategyPlugin(Protocol):
    def metadata(self) -> StrategyMetadata: ...
    def parameter_schema(self) -> dict: ...
    def validate_context(self, context: StrategyContext) -> None: ...
    def generate(self, context: StrategyContext) -> StrategyResult: ...
```

`StrategyContext`只提供不可变ID、参数和Artifact引用。不要传入Repository、数据库Session、HTTP Client或Broker Client。

使用Pydantic生成JSON Schema：

```bash
python -m strategy_sdk.export_schemas --output contracts/schemas/strategy-plugin/v1
```

生成结果至少包含：

```text
strategy-context.schema.json
strategy-result.schema.json
strategy-manifest.schema.json
strategy-parameters.schema.json
```

### 4. 实现StrategyRunner Port

```python
class StrategyRunner(Protocol):
    async def execute(
        self,
        version: StrategyVersion,
        context: StrategyContext,
    ) -> StrategyResult: ...
```

第一版实现：

- `FakeStrategyRunner`：测试固定输出、失败、超时和非法结果。
- `BuiltinStrategyRunner`：运行受信任内置策略。
- `QlibStrategyRunner`：把Qlib策略输出转换为统一StrategyResult。
- `IsolatedContainerStrategyRunner`：第三方插件，步骤7实现。

Application层只能依赖Port，不能判断策略来自Qlib还是第三方容器。

### 5. 实现首批内置策略

#### NO_TRADE

```python
class NoTradeStrategy:
    def generate(self, context: StrategyContext) -> StrategyResult:
        return StrategyResult(
            run_id=context.run_id,
            strategy_id=context.strategy_id,
            strategy_version=context.strategy_version,
            as_of=context.as_of,
            rebalance_decision="NO_REBALANCE",
            scores=[],
            target_weights=context.current_weights,
            proposed_changes=[],
            expected_turnover=Decimal("0"),
            estimated_transaction_cost=Decimal("0"),
            estimated_slippage=Decimal("0"),
            reason_codes=["NO_TRADE_BASELINE"],
            warnings=[],
            evidence_refs=[],
            output_artifacts=[],
        )
```

#### LOW_TURNOVER_TOPK

基于Qlib分数，但增加：

- 保留区间。
- 最低持有期。
- 最小排名改善。
- 每次最多变化股票数。
- 最大预计换手率。
- 不可交易股票过滤。

#### MULTI_FACTOR_QUALITY

使用已批准FactorSet，参数只引用Factor ID和权重，不包含任意公式代码。权重和标准化规则版本化。

#### REGIME_OVERLAY

只调整候选风险预算和允许的总目标暴露，不自行生成新股票。它不能提高到RiskPolicy允许上限以上。

所有参数先使用测试配置，生产值必须由回测和ADR批准。

### 6. 实现准入门禁

```python
class StrategyGatePipeline:
    gates = (
        ManifestGate(),
        DeterminismGate(),
        PointInTimeGate(),
        TradabilityGate(),
        WalkForwardGate(),
        CostGate(),
        TurnoverGate(),
        DrawdownGate(),
        RegimeStabilityGate(),
        CorrelationGate(),
        LicenseGate(),
        SecurityGate(),
    )
```

每个Gate返回结构化结果：

```python
class GateResult(BaseModel):
    gate_id: str
    gate_version: str
    status: Literal["PASS", "FAIL", "REQUIRES_REVIEW"]
    observed: dict[str, str | int | float | None]
    threshold_config_version: str
    reason_codes: list[str]
    evidence_refs: list[str]
```

任何硬Gate FAIL都阻止批准。回测收益高不能覆盖许可证、安全、PIT和不可交易状态错误。

### 7. 实现第三方隔离Runner

建立独立`Dockerfile.strategy-runner`，要求：

- 非root。
- 只读根文件系统。
- 无外网。
- 无生产环境变量和Secret挂载。
- 只读输入Artifact。
- 临时输出目录。
- CPU、内存、进程、磁盘和超时限制。
- 固定镜像Digest，不接受可变Tag。

概念配置：

```yaml
read_only: true
network_mode: none
user: "10001:10001"
mem_limit: 2g
cpus: 1
pids_limit: 64
security_opt:
  - no-new-privileges:true
cap_drop:
  - ALL
```

生产环境不要直接挂载Docker Socket。实际Runner优先调用受控Container Job API；本地开发可以使用权限受限的Runner代理。

执行步骤：

```text
校验Manifest和Digest
  -> 创建只读Input Bundle
  -> 启动一次性容器
  -> 等待退出或超时终止
  -> 读取StrategyResult
  -> JSON Schema和金融约束校验
  -> 保存Artifact和运行审计
  -> 清理临时目录和容器
```

### 8. 实现DailyStrategyPipeline

```python
async def run_daily_strategies(command: RunDailyStrategies):
    versions = await registry.find_active(
        market=command.market,
        as_of=command.as_of,
    )

    results = []
    for version in versions:
        context = await context_factory.build(version, command)
        result = await runner_router.for_version(version).execute(version, context)
        validated = result_validator.validate(version, context, result)
        results.append(validated)

    return await snapshot_publisher.publish_atomically(results, command)
```

每个策略失败相互隔离。是否允许部分策略发布必须由发布Policy明确：

- 核心策略失败：整批策略快照失败，沿用上一批并标记STALE。
- 非核心策略失败：成功策略可发布，但批次标记DEGRADED并列出失败策略。
- NO_TRADE基准失败：整批失败。

### 9. 实现原子快照和事件

事务内：

```text
写DailyStrategySnapshot
  -> 写Snapshot Items
  -> 更新latest指针
  -> 写outbox_events
```

发布：

```text
stock.strategy.daily-strategy.published.v1
```

事件只传snapshotId、strategyId/version、asOf、状态、contentHash和Artifact引用，不传完整权重矩阵。

### 10. API与权限

实现：

```text
POST /internal/v1/strategies
POST /internal/v1/strategies/{id}/versions
POST /internal/v1/strategies/{id}/versions/{version}/validate
POST /internal/v1/strategies/{id}/versions/{version}/approve
POST /internal/v1/strategies/{id}/versions/{version}/activate
POST /internal/v1/strategies/{id}/versions/{version}/suspend
POST /internal/v1/runs/daily-strategies
GET  /api/v1/strategy-snapshots/latest
GET  /api/v1/strategy-snapshots/{snapshotId}
```

权限：

- `STRATEGY_SUBMITTER`：只能登记CANDIDATE。
- `STRATEGY_VALIDATOR`：运行验证，不能批准。
- `STRATEGY_APPROVER`：批准，不能伪造验证结果。
- `STRATEGY_OPERATOR`：激活、暂停和回滚。
- Agent身份：只读ACTIVE快照。

### 11. 接入Agent契约

阶段02只建立读取契约和Fake Consumer；真实Agent在阶段08接入。

Agent工具：

```text
getLatestDailyStrategySnapshots
getStrategySnapshot
getStrategyEvaluationSummary
compareActiveStrategySignals
```

工具不提供：

```text
executeStrategySource
activateStrategy
modifyStrategyParameters
approveStrategy
createOrder
```

## 验证命令

```bash
python -m pytest tests/strategy_contract
python -m pytest tests/strategy_golden
python -m pytest tests/strategy_security
python -m pytest tests/strategy_replay
python -m pytest tests/integration/test_daily_strategy_pipeline.py
```

## 测试案例

1. NO_TRADE输出当前权重、零换手和空变化列表。
2. LOW_TURNOVER_TOPK在排名变化不足时返回NO_REBALANCE。
3. 最低持有期内不产生卖出候选。
4. 超过最大换手率时调仓候选被限制或拒绝。
5. CANDIDATE策略不能出现在生产Agent读取接口。
6. 相同输入、参数、种子和镜像Digest产生相同contentHash。
7. 第三方插件访问网络、数据库环境变量和宿主目录均失败。
8. 第三方插件超时、OOM或输出非法Schema时被终止并审计。
9. 一个非核心插件失败不影响其他策略，批次正确标记DEGRADED。
10. NO_TRADE或核心策略失败时保留旧批次并标记STALE。
11. 重复调用相同Idempotency-Key不产生第二份快照。
12. 相同Outbox事件重复消费不重复启动策略批次。
13. 信号日之后才允许形成可成交候选。
14. 停牌或不可交易股票不会出现在可执行变化中。
15. 策略返回Order或审批字段时Schema拒绝。
16. Plugin SDK破坏性Schema变更不能伪装成v1兼容版本。

## 完成条件

- Strategy Registry和Plugin SDK v1稳定并生成跨语言Schema。
- 四个首批策略完成Golden、回测和原子快照测试。
- 新增Fake第三方策略只增加插件包和Manifest，不修改Application层、Agent或Workflow。
- 第三方Runner无生产数据库、模型、NATS和券商访问能力。
- 策略版本、参数、数据、成本模型、代码和镜像Digest均可追溯。
- 日频计算允许长期NO_REBALANCE，不创建组合调仓批次；每日0～2批硬限制由阶段05及以后按ADR-010实现。
- 只有ACTIVE策略快照能进入Agent上下文。
- 所有测试命令通过并记录结果。
