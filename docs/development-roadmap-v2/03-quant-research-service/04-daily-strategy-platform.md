# 03-04 日频策略Registry与Plugin SDK

## 实施步骤

1. 实现StrategyDefinition、StrategyVersion、RebalancePolicy、StrategyEvaluation和DailyStrategySnapshot。
2. 建立`strategy-plugin/v1`的Context、Result和Manifest Schema。
3. 先实现Fake Strategy和NO_TRADE，再实现LOW_TURNOVER_TOPK、多因子质量和Regime Overlay。
4. 内置策略可受信任进程运行；第三方/开源策略默认一次性隔离容器，无外网、数据库和生产Secret。
5. 建立回测、PIT、成本、换手、容量、Regime、Shadow、安全、许可和人工审批门禁。
6. 只有ACTIVE StrategyVersion发布生产快照；正式合并由版本化Ensemble完成，Agent无权改权重。

## 当前实现

- `src/quant_research/strategy.py`冻结`StrategyDefinition`、`StrategyVersion`、`RebalancePolicy`、`StrategyEvaluation`以及`DailyStrategySnapshot`领域契约。
- `StrategyContext`和`StrategyResult`实现`strategy-plugin/v1`最小接口；Context仅允许版本、时间、Artifact引用和参数，不携带数据库、HTTP、消息或券商客户端。
- `InMemoryStrategyRegistry`只允许`CANDIDATE`经样本外评估和人工审批引用后提升为`ACTIVE`，禁止直接跳级。
- `NoRebalanceStrategy`作为首个基准插件，明确返回`NO_REBALANCE`，不产生订单、调仓批次或交易提案。
- `LowTurnoverTopKStrategy`按分数稳定排序选择Top-K并等权生成候选权重；换手不超过策略阈值时返回`NO_REBALANCE`，否则只返回`REBALANCE_CANDIDATE`。
- `MultiFactorQualityStrategy`按版本化因子权重合成质量分数后复用Top-K门禁；缺少因子或因子集合不一致时拒绝运行。
- `RegimeOverlayStrategy`在`RISK_OFF`状态下按受控比例缩放目标权重并返回`RISK_REDUCTION`，正常状态保持基础策略结果。
- `StrategyPluginManifest`冻结`strategy-plugin/v1`声明；非受信插件默认禁止网络、数据库、Secret和宿主写路径，越权声明在加载时拒绝。
- `StrategyGateInput/StrategyGateResult`统一记录PIT、样本外、成本、换手、容量、许可和安全门禁；任何失败项都会阻止Registry激活，并保留失败代码供审计。
- `migrations/002_strategy_metadata.sql`与`PostgresStrategyMetadataRepository`提供策略版本、Gate结果和策略快照的JSONB幂等登记；数据库仅保存元数据和Artifact引用，不保存大对象。
- `StrategyOutboxEvent`、`InMemoryStrategyOutbox`及PostgreSQL Outbox表按`event_id`幂等记录策略快照事件，投递成功后单独标记时间；消息重试不会重复创建业务事件。
- `InMemoryStrategyPublicationStore`将快照ID、内容Hash和`stock.quant.daily-strategy.published.v1`事件绑定后再提交，事件引用不匹配时拒绝发布；生产环境需由PostgreSQL事务实现同等原子性。
- `PostgresStrategyMetadataRepository.publish_snapshot_with_outbox`已在同一事务内写入策略快照和Outbox事件；任一冲突会回滚，重复提交保持幂等。
- Outbox仓储支持按创建顺序读取未发布事件并限制批量大小；只有下游投递成功后才更新`published_at`，失败不标记，允许安全重试。
- FastAPI仅暴露`GET /api/v1/strategies/{strategy_id}/{version}`和`GET /api/v1/strategy-snapshots/{snapshot_id}`只读查询；未知资源返回404，任何写请求返回405，OpenAPI不得出现交易或激活写接口。
- 另提供`GET /api/v1/strategy-runs/{run_id}`查询运行状态、失败原因和快照引用；启动、重试、激活及交易操作均不开放HTTP写接口。
- 策略版本和策略快照查询在设置`QUANT_RESEARCH_DATABASE_URL`时自动读取PostgreSQL，否则使用内存Fixture；两种模式均保持只读和404语义。
- `004_strategy_runs.sql`和`PostgresStrategyMetadataRepository.save_run/get_run`持久化StrategyRun状态、失败原因和快照引用；策略运行查询API在数据库模式下可跨进程恢复。
- `PostgresStrategyRegistry`已将策略注册、读取和激活绑定到PostgreSQL；激活前必须通过完整 Gate、样本外评估和人工审批，激活结果以幂等版本记录保存。
- 策略版本注册记录保持内容不可变；合法生命周期变更通过受控`replace_version`更新状态，避免使用冲突写入绕过版本审计。
- `StrategyRunService`记录策略运行状态和失败原因；失败时返回上一份READY快照的`is_stale=true`副本，仓储中的上一份READY快照保持不变，重复运行按`run_id`幂等。
- `StrategyExecutionService`串联ACTIVE版本、插件Context校验、StrategyResult、DailyStrategySnapshot和Outbox事件；`StrategyOutboxDispatcher`在发布异常时保留pending，成功后才标记，形成可重试Fixture E2E闭环。
- `build_strategy_snapshot`只接受`ACTIVE`版本，生成稳定内容Hash；`InMemoryStrategySnapshotRepository`提供完整快照原子写入和重复幂等。
- 第三方插件容器隔离、PostgreSQL Registry、Outbox、真实策略和Ensemble属于后续组件集成，不在本次最小切片中实现。

```python
class StrategyPlugin(Protocol):
    def validate_context(self, context: StrategyContext) -> None: ...
    def generate(self, context: StrategyContext) -> StrategyResult: ...
```

## 测试

- 日频运行允许返回NO_REBALANCE，不创建组合调仓批次；本服务不拥有DecisionBudgetReservation或RebalanceBatch。
- CANDIDATE不能进入生产快照。
- 第三方插件网络、数据库、宿主写入和Secret访问失败并审计。
- 新插件无需修改Agent/Workflow契约。

专项测试位于`tests/unit/test_strategy.py`，覆盖ACTIVE准入、审批和样本外门禁、策略Gate失败阻断、NO_REBALANCE、Top-K稳定排序与换手阈值、多因子合成、Regime减仓、插件隔离声明、快照幂等、时间语义及禁止订单字段。
