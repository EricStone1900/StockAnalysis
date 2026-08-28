# 09-01 OrderIntent和人工成交回填

## 目标

把有效批准建议转换为人工执行指令，并安全记录提交、成交和撤销。

## 实施步骤

### 1. 创建OrderIntent

```ts
interface OrderIntent {
  orderIntentId: string;
  decisionId: string;
  riskEvaluationId: string;
  accountId: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  quantity: string;
  orderType: 'LIMIT';
  limitPrice?: string;
  validUntil: string;
  status: 'DRAFT' | 'READY' | 'SUBMITTED' | 'PARTIALLY_FILLED' | 'FILLED' | 'CANCELLED' | 'EXPIRED';
  idempotencyKey: string;
}
```

创建前再次检查APPROVED、RiskEvaluation有效、持仓版本和市场状态。

### 2. 人工提交

用户在券商客户端下单后回填brokerReference、submittedAt和实际委托参数。系统不推断券商已接受。

### 3. 成交回填

```ts
const fillSchema = z.object({
  brokerExecutionId: z.string(),
  quantity: decimalStringSchema,
  price: decimalStringSchema,
  fees: decimalStringSchema,
  executedAt: z.string().datetime({ offset: true }),
});
```

幂等键优先使用brokerExecutionId；人工没有该ID时生成明确的人工记录ID并提示重复风险。

### 4. 状态更新

累计成交量决定PARTIALLY_FILLED/FILLED，禁止成交量超过委托量。撤销不删除已有成交。

## 测试案例

1. 未批准建议不能创建READY。
2. 过期RiskEvaluation不能创建指令。
3. 重复brokerExecutionId只入账一次。
4. 部分成交后撤销保留已成交数量。
5. 卖出数量违反T+1时拒绝创建指令。

## 完成条件

- 全部人工动作有operatorId和审计。
- OrderIntent状态机不可跳跃。
- 成交回填不会直接执行跨SchemaSQL。

