# 12-03 Broker Adapter与自动执行

## 实施步骤

1. 定义BrokerPort的place、cancel、query、positions和fills；先用Broker认证测试环境完成Contract。
2. Adapter将内部SecurityId、Decimal和OrderType映射为券商协议，保存外部Request/Order/Fill ID。
3. 自动执行只允许白名单账户、标的、时段、最大金额和已批准策略版本。
4. 下单前再次校验Proposal、RiskReview、RiskEvaluation、Approval、价格偏差、交易批次和Kill Switch。
5. 请求超时后先query，不确定状态标UNKNOWN，禁止自动重下。
6. Web提供双人审批、暂停、恢复和只读订单时间线。

```ts
interface BrokerPort {
  place(command: BrokerOrderCommand): Promise<BrokerOrderResult>;
  query(clientOrderId: string): Promise<BrokerOrderState>;
  cancel(clientOrderId: string): Promise<BrokerOrderState>;
}
```

## 测试

- 请求成功但响应丢失、重复回报、乱序Fill和Broker断线。
- 白名单、金额、时段、过期和价格偏差拒绝。
- UNKNOWN不自动重下。

