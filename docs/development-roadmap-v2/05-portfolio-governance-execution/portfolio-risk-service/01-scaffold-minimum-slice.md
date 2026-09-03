# Portfolio 05-01 骨架与最小纵向切片

## 当前实现

已建立TypeScript领域骨架和`PortfolioLedger`最小切片。人工期初持仓导入会校验Decimal字符串精度、正数量、事件时间和
必填审计字段，使用`expectedVersion`防止并发覆盖，并用`Idempotency-Key`避免重复入账。持仓按证券代码稳定排序，生成
不可变`PortfolioSnapshot`和规范内容Hash；原始账本事实不提供原地修改接口。

NestJS已提供`POST /api/v1/portfolios/{portfolioId}/manual-snapshots`和最新快照查询入口。已补充
`migrations/001_portfolio_ledger.sql`以及参数化的`PostgresPortfolioRepository`：账本、快照和幂等记录分别保存，快照
payload与Hash一并落库，便于审计和重放。设置`PORTFOLIO_DATABASE_URL`后，NestJS组合根会启动时执行幂等迁移并使用
事务仓储；未设置时仍使用内存模式，便于Mac本地快速开发。本步骤不接收TradeProposal、不创建Approval或Order。
数据库模式下每次写入前会读取最新快照并恢复对应 Portfolio 的账本版本，服务重启后仍能执行`expectedVersion`并发保护；不同 Portfolio 的版本互不干扰。
并发请求若触发 PostgreSQL 唯一约束（`23505`），应用会重新读取幂等记录并返回已提交快照，避免把正常竞态误报为服务器错误。
集成测试已验证两个独立服务实例并发提交相同命令时只返回同一份已提交快照；重读最多重试 3 次且每次间隔 10ms。
领域层和 PostgreSQL 均已支持冲正：原始 Entry 不修改，新增带 `reversal_of_entry_id` 的 `REVERSAL` Entry，数据库唯一索引禁止重复冲正；相同冲正幂等键返回首次结果。

## 实施步骤

1. 从Node模板创建独立服务、数据库迁移和持久化端口。
2. 建立Portfolio、Account、CashBalance、Position和LedgerEntry模型。
3. 最小Use Case为“人工导入期初持仓并发布PortfolioSnapshot”。
4. 写命令使用Idempotency-Key和expectedVersion；LedgerEntry不可原地修改，只能冲正。
5. 保存来源、actor、occurredAt、availableAt和审计原因。

```ts
interface LedgerEntry {
  entryId: string;
  portfolioId: string;
  type: 'OPENING' | 'BUY' | 'SELL' | 'FEE' | 'DIVIDEND' | 'REVERSAL';
  securityId?: string;
  quantity?: string;
  amount: string;
  occurredAt: string;
  sourceRef: string;
}
```

## 本步验证

- `COREPACK_HOME="$PWD/.corepack" pnpm --filter @stock/portfolio-risk-service lint`
- `COREPACK_HOME="$PWD/.corepack" pnpm --filter @stock/portfolio-risk-service typecheck`
- `COREPACK_HOME="$PWD/.corepack" pnpm --filter @stock/portfolio-risk-service test`
- 单元测试覆盖重复导入、版本冲突、Decimal精度、参数化SQL以及最新快照查询。
- 已通过真实PostgreSQL集成测试：迁移可重复执行、快照可读回、幂等记录可查询，后续写入失败会整体回滚；未配置数据库时集成测试明确跳过。
- API层测试覆盖成功响应、`409 Conflict`版本冲突、`400 Bad Request`输入错误和`404 Not Found`缺失快照。
- 容器启动时以`PORTFOLIO_DATABASE_URL`选择数据库模式；Compose服务映射到宿主机`3002`端口。
