# 00-02 依赖、契约和时间语义

## 实施步骤

1. 绘制编译依赖、同步运行依赖、异步事件依赖和人工依赖四张矩阵。
2. 明确REST用于即时查询/命令，NATS用于领域事实，Temporal用于长流程和人工等待。
3. 为所有写命令统一`Idempotency-Key`、`actorId`、`correlationId`和`expectedVersion`。
4. 为事件统一eventId、occurredAt、availableAt、producer、schemaVersion、correlationId和causationId。
5. 固化Asia/Shanghai、交易所日历、UTC存储、Decimal和SecurityId规则。
6. 定义数据与证据新鲜度、过期、未来可见性和历史回放规则。

事件信封骨架：

```ts
interface DomainEventEnvelope<T> {
  eventId: string;
  subject: string;
  schemaVersion: number;
  occurredAt: string;
  availableAt: string;
  correlationId: string;
  causationId?: string;
  producer: string;
  payload: T;
}
```

## 测试

- Schema缺少availableAt时生成失败。
- 破坏性事件变更必须更换Subject Major版本。
- 依赖图检查不允许Domain依赖Adapter或跨服务ORM包。

## 完成条件

共享契约草案可以生成TypeScript和Python类型；时间语义有可执行Fixture。

