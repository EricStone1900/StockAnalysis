# 阶段12测试计划

- Paper成交、费用、滑点、部分成交和不可交易。
- Shadow无写权限、PIT成交模拟和策略账本隔离。
- Broker Contract、认证、限流、断线、UNKNOWN、乱序和重复回报。
- 下单前全部版本、新鲜度、白名单、价格和批次检查。
- Kill Switch各层级、独立故障和恢复。
- Paper/Shadow/生产数据库、Secret和网络隔离。
- 日终对账、灾难恢复、Secret轮换和审计。
- 小资金上线前长周期容量、错误率、滑点和回撤报告。

任何UNKNOWN重复下单、跨环境污染或Kill Switch失效都判定FAIL。

