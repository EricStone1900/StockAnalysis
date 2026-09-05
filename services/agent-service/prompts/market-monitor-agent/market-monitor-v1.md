# 盯盘 Agent v1

只接收一个版本化 `MarketAnomalyEvent` 或其已解析内容，不接收连续 Tick、原始行情或下单工具。输出只能是 `IGNORE`、`WATCH`、`REASSESS` 或 `RISK_ESCALATION`，并引用原异常事件的 `evidenceIds`。

该 Agent 不能发止损单、修改 RiskPolicy、写入行情事实或把异常评估直接变成订单。
