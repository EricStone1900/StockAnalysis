# Portfolio 05-01 骨架与最小纵向切片

## 当前实现

已建立TypeScript领域骨架和`PortfolioLedger`最小切片。人工期初持仓导入会校验Decimal字符串精度、正数量、事件时间和
必填审计字段，使用`expectedVersion`防止并发覆盖，并用`Idempotency-Key`避免重复入账。持仓按证券代码稳定排序，生成
不可变`PortfolioSnapshot`和规范内容Hash；原始账本事实不提供原地修改接口。

NestJS已提供`POST /api/v1/portfolios/{portfolioId}/manual-snapshots`和最新快照查询入口。当前仓储为内存实现，账本
PostgreSQL迁移、冲正流水、估值与RiskPolicy属于后续切片；本步骤不接收TradeProposal、不创建Approval或Order。

## 实施步骤

1. 从Node模板创建独立服务、数据库和迁移。
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

## 测试

- 重复导入不重复入账。
- 非法负数量、未知证券、Decimal精度和并发版本冲突。
- 冲正后原Entry仍保留。
- 快照总额和明细一致。
