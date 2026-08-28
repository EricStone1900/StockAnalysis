# 10-01 Paper Trading模拟成交

## 目标

在不连接真实券商的情况下验证订单状态、费用、滑点、部分成交和对账。

## 实施步骤

### 1. 执行Adapter

```ts
interface ExecutionAdapter {
  submit(intent: OrderIntent): Promise<ExecutionAck>;
  cancel(orderId: string): Promise<ExecutionAck>;
  getOrder(orderId: string): Promise<OrderSnapshot>;
}
```

实现`PaperExecutionAdapter`，业务状态机不依赖具体Adapter。

### 2. 成交模型

第一版配置：

- 限价是否穿过Bar价格。
- 参与率上限。
- 固定/比例滑点。
- 佣金、印花税、过户费。
- 涨跌停、停牌和T+1。
- 部分成交与过期。

```ts
const fillable = Math.min(intent.quantity, bar.volume.mul(participationRate));
```

Decimal计算并固定舍入规则。

### 3. 环境隔离

Paper账户、数据库标识、Order ID前缀和Dashboard必须醒目标记，禁止与人工真实记录混合。

### 4. 比较

将模拟成交与人工实际成交比较滑点、成交率和延迟，校准但不使用未来Bar价格。

## 测试案例

1. 未触及限价不成交。
2. 成交量不足产生部分成交。
3. 涨停买入和跌停卖出按规则处理。
4. 重复提交相同幂等键不创建两张模拟订单。
5. 费用与A股规则版本一致。

## 完成条件

- Paper路径通过与人工路径相同的批准和硬风控。
- 模拟状态可以完整对账和回放。
- 模拟结果不会更新真实组合。

