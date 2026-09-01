# Execution 05-02 人工Fill、对账与强化

## 实施步骤

1. 实现人工提交记录、部分成交、多次Fill、费用、撤单和过期。
2. Fill使用外部成交标识加账户唯一约束；发布不可变FillRecorded事件。
3. 接portfolio-risk Fill命令，依靠双方Inbox/Idempotency防止重复入账。
4. 实现日终对账：系统Intent/Fill与人工券商对账文件比较，差异进入人工队列。
5. 建立BrokerPort但只接Fake/文件Adapter，为阶段12预留。
6. 实现执行暂停、紧急停止和完整审计。
7. 批次原子接受成功后通知Governance消费DISPATCHING预算预留；明确未接受时通知释放，响应不确定时提供按批次ID/幂等键查询，接受后任何终态均不请求释放。
8. 汇总子OrderIntent和Fill得到RebalanceBatch状态；部分成交、撤单重报和同批幂等重试不创建新批次。

## 测试

- 重复Fill只记一次，部分成交汇总正确。
- 对账缺单、多单、数量、价格和费用差异。
- 发布Fill后进程崩溃，恢复仍可入账一次。
- UNKNOWN、网络超时Fixture不会自动重下单。
- 多Leg原子创建、预算消费/释放、接受后失败不恢复额度。
