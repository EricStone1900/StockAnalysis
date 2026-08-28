# Execution 05-02 人工Fill、对账与强化

## 实施步骤

1. 实现人工提交记录、部分成交、多次Fill、费用、撤单和过期。
2. Fill使用外部成交标识加账户唯一约束；发布不可变FillRecorded事件。
3. 接portfolio-risk Fill命令，依靠双方Inbox/Idempotency防止重复入账。
4. 实现日终对账：系统Intent/Fill与人工券商对账文件比较，差异进入人工队列。
5. 建立BrokerPort但只接Fake/文件Adapter，为阶段12预留。
6. 实现执行暂停、紧急停止和完整审计。

## 测试

- 重复Fill只记一次，部分成交汇总正确。
- 对账缺单、多单、数量、价格和费用差异。
- 发布Fill后进程崩溃，恢复仍可入账一次。
- UNKNOWN、网络超时Fixture不会自动重下单。

