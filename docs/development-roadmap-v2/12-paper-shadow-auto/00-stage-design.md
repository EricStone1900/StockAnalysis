# 阶段12：Paper、Shadow与受控自动交易

## 目标

人工闭环和学习门禁长期稳定后，依次进入Paper Trading、Shadow Trading和小资金白名单自动交易。禁止跨级上线。

## 顺序

1. [Paper Trading](./01-paper-trading.md)。
2. [Shadow与决策对照](./02-shadow-trading.md)。
3. [Broker Adapter和自动执行](./03-broker-auto-execution.md)。
4. [Kill Switch、容量和生产强化](./04-safety-scale.md)。
5. [测试](./90-test-plan.md)与[验收](./99-acceptance.md)。

## 进入条件

- 阶段10人工对账无未解决差异并稳定运行足够周期。
- 阶段10日频与盘中联合回放通过；拟启用的第二批reason、MonitorPolicy（10/20/30分钟分层评估）、阈值和回滚条件已有签署记录。
- Agent、风险、审批、执行和Memory审计完整。
- Paper/Shadow环境与生产账户、Secret、数据库和网络隔离。
- 自动交易Feature Flag默认关闭，开启需要独立审批。
- RebalanceBatch、预算预留和OrderIntent父子状态语义保持与人工环境一致，不因自动化重新定义批次计数。
