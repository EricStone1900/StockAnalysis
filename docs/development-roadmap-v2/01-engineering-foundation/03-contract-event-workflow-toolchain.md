# 01-03 契约、事件与工作流工具链

## 实施步骤

1. `packages/contracts`保存OpenAPI、AsyncAPI、JSON Schema源文件，不保存手写重复DTO。
2. 生成TypeScript Client/Types和Python Pydantic模型，并在CI检查生成结果无漂移。
3. 建立Transactional Outbox和Inbox通用库；领域服务只依赖Port。
4. 建立Fake HTTP Server、Fake Event Publisher和Contract Fixture工具。
5. 建立Temporal TypeScript Worker骨架、Activity错误分类和测试环境。

Outbox端口：

```ts
interface UnitOfWork {
  execute<T>(work: (tx: Transaction) => Promise<T>): Promise<T>;
}

interface OutboxWriter {
  append(event: DomainEventEnvelope<unknown>, tx: Transaction): Promise<void>;
}
```

业务状态和Outbox必须在同一数据库事务提交；NATS发布失败由Relay重试。

## 测试

- OpenAPI破坏性变化检查。
- 同一eventId重复10次，Inbox Handler副作用一次。
- 数据提交后进程崩溃，Outbox Relay恢复后仍发布。
- Temporal Workflow代码确定性测试。

