# trade-execution-service

## 1. 定位

交易指令和成交状态的唯一执行边界。当前阶段只支持人工执行记录；未来依次扩展模拟盘、影子交易和券商自动交易。

本服务只接收 decision-governance-service 已批准且风控有效的指令草稿。

## 2. 分阶段能力

### 阶段一：人工执行

- 展示已批准指令。
- 生成建议委托数量、价格参考和有效期。
- 用户在券商客户端人工下单。
- 用户回填成交或撤销结果。
- 更新订单状态并请求 portfolio-risk-service 入账。

### 阶段二：模拟盘

- 使用市场数据模拟订单接受、部分成交、滑点和费用。
- 验证状态机、对账和异常补偿。
- 与真实行情回放对比。

### 阶段三：影子交易

- 生成真实时间下的模拟订单但不发送券商。
- 对比理论成交和真实可成交性。
- 评估延迟、频率和风险策略。

### 阶段四：受控自动交易

- 接入 Broker Adapter。
- 小资金、白名单股票和严格限额。
- 支持 Kill Switch、只减仓和人工接管。

## 3. 内部模块

    ApprovedInstructionConsumer
    RebalanceBatchFactory
    RebalanceBatchStateMachine
    OrderIntentValidator
    OrderStateMachine
    ManualExecutionAdapter
    PaperTradingAdapter
    BrokerAdapterRegistry
    FillProcessor
    ReconciliationEngine
    ExecutionAudit

## 4. 调仓批次与订单状态机

一个已批准的组合级TradeProposal原子创建一个RebalanceBatch及多个OrderIntent。若任一Leg在创建前校验失败，整个批次拒绝，不得留下部分READY Intent。

RebalanceBatch状态：

    ACCEPTED
      -> IN_PROGRESS
      -> PARTIALLY_FILLED
      -> COMPLETED

分支状态：

    CANCELLED
    EXPIRED
    FAILED
    UNKNOWN

OrderIntent状态：

    DRAFT
      -> READY
      -> SUBMITTED
      -> ACCEPTED
      -> PARTIALLY_FILLED
      -> FILLED

分支状态：

    REJECTED
    CANCEL_PENDING
    CANCELLED
    EXPIRED
    UNKNOWN

UNKNOWN 表示发送结果或券商状态无法确认，必须查询或人工处理，不能自动当作失败后重新下单。

## 5. 指令校验

原子接受RebalanceBatch前检查：

- decisionId 状态为 APPROVED。
- hardRiskEvaluation 仍在有效期。
- budgetReservationId有效、状态为DISPATCHING，且decisionId和proposalVersion一致；RESERVED不得直接接受，遵循ADR-010。
- targetPortfolioVersion、Leg集合和contentHash与批准版本一致。
- portfolioSnapshotId 与当前状态未发生不可接受偏差。
- 指令未过期。
- 当前没有相同 idempotencyKey 的订单。
- 市场、证券状态和交易时间允许。
- 系统没有启用 Kill Switch。

批次与全部DRAFT/READY OrderIntent持久化成功后才返回ACCEPTED，并请求decision-governance-service把DISPATCHING预留转为CONSUMED。原子接受明确失败时不得创建任何READY Intent，并请求释放预留；结果不确定时必须支持按rebalanceBatchId或幂等键查询。接受成功后，部分成交、撤销、过期、重报或失败均不释放调仓额度。

Execution本地事务与Governance预算事务不组成分布式事务；接受结果通过同步响应、Outbox事件和幂等查询恢复。Governance仍为RESERVED或DISPATCHING时，不表示可以创建第二个替代批次。

## 6. API

当前人工模式：

- POST /internal/v1/rebalance-batches
- GET /api/v1/rebalance-batches/{rebalanceBatchId}
- POST /internal/v1/order-intents
- GET /api/v1/order-intents
- GET /api/v1/order-intents/{orderIntentId}
- POST /api/v1/order-intents/{orderIntentId}/record-submission
- POST /api/v1/order-intents/{orderIntentId}/record-fill
- POST /api/v1/order-intents/{orderIntentId}/record-cancellation

未来自动模式：

- POST /internal/v1/orders/{orderIntentId}/submit
- POST /internal/v1/orders/{orderId}/cancel
- GET /internal/v1/orders/{orderId}/refresh
- POST /internal/v1/reconciliation/run

## 7. Broker Adapter

统一接口至少包含：

- getAccounts。
- getBalances。
- getPositions。
- placeOrder。
- cancelOrder。
- getOrder。
- listOrders。
- listFills。

每个 Adapter 声明支持的市场、订单类型、交易时段、幂等能力和限流规则。业务层不依赖具体券商 SDK 类型。

## 8. A股执行约束

规则按日期和市场版本化：

- T+1。
- 最小交易单位。
- 涨跌停和停牌。
- 委托价格范围。
- 手续费、印花税和过户费。
- 部分成交。
- 订单有效时间。
- 除权除息和证券代码状态。

规则变化通过配置发布，不在 Adapter 中散落硬编码。

## 9. 对账

    券商成交回报
      -> Fill 标准化
      -> 去重
      -> 更新订单状态
      -> portfolio-risk-service 入账
      -> 日终账户、持仓和现金对账

差异产生 ReconciliationIssue，不自动覆盖本地流水。人工确认或补偿流程完成后再修正。

## 10. 安全

- 券商密钥使用独立 Secrets Manager，Agent和前端无法读取。
- 自动下单权限默认关闭，通过 Feature Flag 和账户白名单启用。
- Kill Switch 必须在模型、工作流和券商 Adapter 之外独立生效。
- 所有下单操作写防篡改审计。
- 生产与模拟环境使用不同账户、密钥和数据库标识。

## 11. 后续扩展

- 多券商和智能路由。
- 限价、TWAP 等执行算法，但低频系统初期不需要复杂算法。
- 实时订单推送和断线恢复。
- 自动撤单和超时策略。
- 多市场结算周期。
- 灾难恢复和人工接管控制台。

## 12. 验收标准

- 重复提交同一指令不会产生重复订单。
- UNKNOWN 状态不会自动重下单。
- 只有有效批准和有效风控结果才能创建 READY 指令。
- 所有成交都能追溯到 decisionId、orderIntentId 和券商回报。
- 一个批准的组合级Proposal原子生成一个RebalanceBatch和多个OrderIntent，任何Leg失败都不会留下部分READY批次。
- 同一rebalanceBatchId或幂等键重复提交不会重复创建批次或占用第二个预算名额。
