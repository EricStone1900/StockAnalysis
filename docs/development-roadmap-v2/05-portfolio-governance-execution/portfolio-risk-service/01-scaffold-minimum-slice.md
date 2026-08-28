# Portfolio 05-01 骨架与最小纵向切片

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

