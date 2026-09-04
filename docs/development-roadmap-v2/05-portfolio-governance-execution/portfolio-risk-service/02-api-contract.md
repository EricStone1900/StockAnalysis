# Portfolio 风险服务 API 契约（05-01）

## 期初快照导入

`POST /api/v1/portfolios/{portfolioId}/manual-snapshots`

请求必须携带 `Idempotency-Key` 和 `X-Actor-Id`（分别与 body 中的 `idempotencyKey`、`actorId` 保持一致），并提交：

```json
{
  "accountId": "account-1",
  "cash": "100000.00",
  "positions": [{"securityId": "SSE:600000", "quantity": "100"}],
  "occurredAt": "2026-09-03T01:00:00Z",
  "availableAt": "2026-09-03T01:00:00Z",
  "sourceRef": "manual-import-1",
  "actorId": "operator-1",
  "reason": "期初导入",
  "expectedVersion": 0,
  "idempotencyKey": "opening-1"
}
```

金额和数量使用十进制字符串，最多 8 位小数；`availableAt` 不得早于 `occurredAt`。成功返回 `PortfolioSnapshot`，包括 `snapshotId`、`ledgerVersion`、稳定排序的 `positions`、`contentHash` 和审计来源字段。

## 最新快照查询

`GET /api/v1/portfolios/{portfolioId}/snapshots/latest` 返回最新快照；不存在返回 `404`。

## 流水冲正

`POST /api/v1/portfolios/{portfolioId}/ledger-entries/{entryId}/reversals` 新增一条冲正流水。请求体字段为
`occurredAt`、`availableAt`、`sourceRef`、`actorId`、`reason`、`expectedVersion` 和 `idempotencyKey`；请求头
`Idempotency-Key` 必须与 body 一致。原流水不会被修改，重复冲正返回 `400`，版本冲突返回 `409`。

## 确认成交入账（内部）

`POST /internal/v1/reconciliation/apply-confirmed-fill` 仅接受人工确认或券商确认的成交。请求需携带
`portfolioId`、`securityId`、`side`（`BUY`或`SELL`）、`quantity`、`price`、`fee`、时间、来源、审计字段、
`expectedVersion`及`idempotencyKey`，并要求 `Idempotency-Key`、`X-Actor-Id` 和 `X-Correlation-Id` 请求头。

同一请求原子生成成交流水、可选费用流水与新快照；卖超可用持仓返回 `400`，版本过期返回 `409`。本阶段不接受未经确认的成交或订单指令。

## 现金分红入账（内部）

`POST /internal/v1/reconciliation/apply-cash-dividend` 接收已确认的现金分红：`portfolioId`、`securityId`、`cashPerShare`、时间、来源、审计字段、`expectedVersion` 和 `idempotencyKey`。系统以当前持仓数量计算分红金额，原子写入 `DIVIDEND` 流水和新版快照；无该证券持仓返回 `400`。拆股、送股等数量变化操作尚未开放。

## 拆股或送股比例调整（内部）

`POST /internal/v1/reconciliation/apply-stock-split` 接收 `portfolioId`、`securityId`、正整数 `numerator`/`denominator`、时间、来源、审计字段、`expectedVersion` 和 `idempotencyKey`。它按比例调整该证券数量和可用数量，现金保持不变，并原子写入 `SPLIT` 流水与新版快照。

## 错误与幂等

- `400`：字段缺失、格式错误或数量非正数。
- `409`：同一 Portfolio 的 `expectedVersion` 过期。
- `403`：缺少或伪造 `X-Actor-Id`（生产环境还需由网关身份声明映射到该值）。
- `400`：缺少 `X-Correlation-Id`；该请求头用于日志、审计和后续事件链路关联。
- `X-Correlation-Id` 会写入账本流水的 `correlation_id` 字段，旧数据为空时仍可读取。
- 相同 Portfolio 与 `Idempotency-Key` 重复请求返回首次快照；并发唯一键冲突会重新读取已提交快照。
- 冲正流水也持久化 `idempotency_key`；服务重启后相同冲正键仍返回首次 `REVERSAL` 事实。
- 本阶段不提供交易、审批、Order 或 RiskPolicy 写接口。
