# 12-04 Kill Switch、容量和生产强化

## 实施步骤

1. Kill Switch独立于Agent、NATS和Temporal，Execution下单前同步读取并本地失败关闭。
2. 建立账户级、策略级、标的级和全局级暂停；风险下降卖出是否允许由明确政策决定。
3. 监控订单UNKNOWN、拒单率、滑点、成交延迟、持仓差异、回撤、数据新鲜度和Provider状态。
4. 实现券商对账、灾难恢复、Secret轮换、双人操作和审计导出。
5. 容量和可用性需求明确后才考虑Kubernetes、多副本和服务拆分；不能为了技术偏好提前扩容。
6. 自动化按Paper -> Shadow -> 小资金白名单 -> 多账户受控扩展逐级审批。

## 演练

- Agent异常持续BUY时硬风控和Kill Switch阻断。
- NATS/Temporal/数据库/券商分别故障。
- Kill Switch启用时所有新增订单同步失败。
- 恢复后不自动补下故障期间的旧订单。

