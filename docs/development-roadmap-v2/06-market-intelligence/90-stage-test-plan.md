# 阶段06集成测试计划

1. 同一SecurityId在新闻、盯盘和Regime中一致。
2. 新闻迟到、分钟乱序和Regime数据缺失分别受控处理。
3. 相同eventId重复10次无重复副作用。
4. Fake Agent结果重复回写幂等。
5. NATS停止和恢复后Outbox事件完整补发。
6. 删除任一服务投影后可由事实/API重建。
7. 三服务数据库账号互相写入被拒绝。

测试必须分别运行单服务Component Suite和三服务契约Suite。

