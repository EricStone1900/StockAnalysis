# Portfolio 风险服务 API 契约（05-01）

## 期初快照导入

`POST /api/v1/portfolios/{portfolioId}/manual-snapshots`

请求必须携带 `Idempotency-Key`（当前版本同时要求 body 中的 `idempotencyKey` 与其保持一致），并提交：

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

## 错误与幂等

- `400`：字段缺失、格式错误或数量非正数。
- `409`：同一 Portfolio 的 `expectedVersion` 过期。
- 相同 Portfolio 与 `Idempotency-Key` 重复请求返回首次快照；并发唯一键冲突会重新读取已提交快照。
- 本阶段不提供交易、审批、Order 或 RiskPolicy 写接口。
