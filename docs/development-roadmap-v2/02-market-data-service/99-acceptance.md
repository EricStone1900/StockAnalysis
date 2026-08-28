# market-data-service验收

- [ ] 服务可独立构建、迁移和启动。
- [ ] Security/Calendar最小切片通过。
- [ ] 日线、财务事实和公司行动标准化通过。
- [ ] PIT与未来数据泄漏测试通过。
- [ ] DataVersion原子发布和失败保旧版本通过。
- [ ] Qlib不可变数据视图可生成。
- [ ] OpenAPI、事件、Outbox/Inbox和重复测试通过。
- [ ] 供应商故障、回补、恢复和观测通过。
- [ ] 可以从原始Artifact重建相同版本和Hash。

验收后冻结DataVersion v1契约，阶段03只能通过API/Artifact引用消费。

