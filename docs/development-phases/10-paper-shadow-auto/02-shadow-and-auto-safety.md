# 10-02 Shadow Trading与自动交易安全

## 目标

先在真实时间生成不发送的影子订单，再以白名单、小额度接入券商自动交易。

## 实施步骤

### 1. Shadow模式

Shadow使用实时数据和真实决策时间，但Execution Adapter只能保存`WOULD_SUBMIT`，没有网络下单能力。

比较：可成交性、建议到订单延迟、价格偏差、错过交易和风控结果。

### 2. Broker Adapter边界

```ts
interface BrokerAdapter {
  capabilities(): BrokerCapabilities;
  placeOrder(request: BrokerOrderRequest): Promise<BrokerOrderAck>;
  cancelOrder(brokerOrderId: string): Promise<BrokerOrderAck>;
  getOrder(brokerOrderId: string): Promise<BrokerOrderSnapshot>;
  listFills(since: string): Promise<BrokerFill[]>;
}
```

业务层不使用券商SDK类型。

### 3. 独立安全控制

- Kill Switch：阻止新订单。
- REDUCE_ONLY：只允许降低暴露。
- 账户、股票、金额白名单。
- 每日累计额度和订单数。
- 人工接管。

这些控制在Broker调用前确定性执行，不依赖LLM响应。

### 4. UNKNOWN状态

超时后无法确认是否受理时标记UNKNOWN，查询券商状态或人工处理；禁止自动当失败后重下单。

### 5. 密钥

交易密钥只提供给独立execution进程。Agent、Web和监控Worker无读取权限。

## 测试案例

1. Shadow模式网络层无法调用券商。
2. Kill Switch在模型仍运行时阻止订单。
3. 非白名单股票被拒绝。
4. UNKNOWN不会自动重下单。
5. REDUCE_ONLY拒绝增加绝对仓位的操作。
6. 券商重复回报按brokerExecutionId去重。

## 完成条件

- Shadow运行达到ADR规定观察期。
- Kill Switch完成独立故障注入测试。
- 自动交易默认关闭且需显式发布配置开启。

