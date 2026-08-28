# 阶段10：模拟盘、影子和受控自动交易总设计

## 目标

在人工作业稳定后，依次验证模拟成交、真实时间影子交易和小资金白名单自动交易。

## 强制进入条件

- 数据、快照、Agent和工作流已稳定运行足够观察周期。
- 人工成交对账无未解决差异。
- 风控、审批、审计和Kill Switch完成独立测试。
- 已完成生产/模拟账户和密钥隔离ADR。

## 实施要求

- 严格按Paper、Shadow、小资金白名单顺序推进。
- Shadow进程物理上不能发送券商订单。
- Kill Switch和REDUCE_ONLY独立于Agent和Temporal生效。
- UNKNOWN订单状态必须查询或人工处理，禁止自动重下单。

## 顺序文档

1. [Paper Trading模拟成交](./01-paper-trading.md)
2. [Shadow Trading与自动交易安全](./02-shadow-and-auto-safety.md)
3. [服务拆分、扩容和上线门禁](./03-service-split-and-scale.md)

## 阶段验收

- 模拟成交包含滑点、费用、部分成交和交易规则。
- 影子交易不向券商发送订单。
- Kill Switch和只减仓模式独立于LLM生效。
- 自动交易仅对白名单账户、股票和额度开放。
- UNKNOWN订单状态不会自动重下单。
