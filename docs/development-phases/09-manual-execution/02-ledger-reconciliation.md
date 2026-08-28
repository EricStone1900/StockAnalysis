# 09-02 组合流水和日终对账

## 目标

把确认成交转换为不可变PortfolioLedger记录，生成新PortfolioSnapshot并发现人工记录差异。

## 实施步骤

### 1. Ledger事件

```ts
type LedgerEntryType = 'CASH_DEPOSIT' | 'CASH_WITHDRAWAL' | 'BUY_FILL' | 'SELL_FILL' | 'FEE' | 'ADJUSTMENT';

interface LedgerEntry {
  ledgerEntryId: string;
  sourceId: string;
  type: LedgerEntryType;
  effectiveAt: string;
  amount: string;
  symbol?: string;
  quantity?: string;
}
```

流水追加写，不原地修改。纠错使用ADJUSTMENT并引用原记录。

### 2. 成交应用事务

```ts
await db.transaction(async tx => {
  await fillDeduplicator.assertNew(fill.brokerExecutionId, tx);
  await ledger.append(entriesFromFill(fill), tx);
  await outbox.enqueue({ type: 'PortfolioLedgerChanged', fillId: fill.fillId }, tx);
});
```

### 3. 快照重建

从指定ledgerVersion和MarketDataVersion重算现金、数量、成本和盈亏。不要把浮动盈亏混入现金流水。

### 4. 日终对账

输入人工券商账户截图/导出后的标准记录，比较现金、持仓、成交和费用。差异生成ReconciliationIssue，不能自动覆盖流水。

## 测试案例

1. 买入同时减少现金、增加持仓并记录费用。
2. 卖出计算已实现盈亏且不重复扣费。
3. 重放全部流水得到相同快照。
4. 重复Fill不改变ledgerVersion。
5. 对账差异生成Issue并等待人工确认。

## 完成条件

- 组合可从流水重建。
- 快照与成交建立完整引用。
- 日终对账有操作页面或受控命令。

