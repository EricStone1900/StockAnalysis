# 00-03 共享契约与代码生成

## 目标

建立OpenAPI、AsyncAPI和JSON Schema唯一契约源，生成TypeScript和Python类型，避免跨语言手写重复结构。

## 实施步骤

### 1. 定义基础Schema

先实现：`DataFreshness`、`ProvenanceRef`、`EventEnvelope`、`ErrorEnvelope`和`JobAccepted`。

JSON Schema示例：

```json
{
  "$id": "DataFreshness.v1",
  "type": "object",
  "additionalProperties": false,
  "required": ["asOf", "availableAt", "isStale"],
  "properties": {
    "asOf": { "type": "string", "format": "date-time" },
    "availableAt": { "type": "string", "format": "date-time" },
    "latestExpectedAt": { "type": "string", "format": "date-time" },
    "isStale": { "type": "boolean" },
    "staleReason": { "type": "string" }
  }
}
```

`additionalProperties: false`用于尽早发现拼写和版本不兼容，不应依赖模型输出中的额外字段。

### 2. 生成语言包

推荐流水线：

```text
contracts/openapi + contracts/asyncapi + contracts/schemas
  -> validate
  -> generate packages/contracts
  -> generate python/packages/contracts-py
  -> compile generated packages
  -> compatibility tests
```

TypeScript生成结果外再提供Zod运行时校验：

```ts
export const dataFreshnessSchema = z.object({
  asOf: z.string().datetime({ offset: true }),
  availableAt: z.string().datetime({ offset: true }),
  latestExpectedAt: z.string().datetime({ offset: true }).optional(),
  isStale: z.boolean(),
  staleReason: z.string().optional(),
}).strict();
```

Python生成Pydantic模型：

```python
class DataFreshness(BaseModel):
    model_config = ConfigDict(extra="forbid")
    as_of: AwareDatetime
    available_at: AwareDatetime
    latest_expected_at: AwareDatetime | None = None
    is_stale: bool
    stale_reason: str | None = None
```

JSON字段保持camelCase；Python内部可通过alias映射snake_case。

### 3. 版本和兼容性

- 新增可选字段：兼容。
- 删除、重命名、改变语义或收窄枚举：破坏性变更。
- 事件破坏性变更发布新的Subject Major版本；新旧消费者在迁移窗口并存。
- HTTP破坏性变更创建`/v2`。

### 4. 定义AsyncAPI和Subject

每个领域事件必须声明producer、consumer、NATS Subject、EventEnvelope和Payload Schema。Subject使用`stock.<context>.<topic>.<past-event>.v<major>`，例如`stock.quant.daily-analysis.published.v1`。

### 5. 契约Fixture

为每个Schema保存至少一个合法和多个非法样例，包括缺失字段、额外字段、错误时区和越界数值。

## 测试

```bash
pnpm contracts:validate
pnpm contracts:generate
pnpm contracts:asyncapi:validate
pnpm --filter @stock/contracts test
python -m pytest tests/contract
```

## 完成条件

- 连续运行两次生成命令结果一致。
- TS和Python对同一Fixture得出相同通过/拒绝结论。
- 生成文件顶部标明“禁止手工编辑”。
- CI能发现未提交的生成结果漂移。
- AsyncAPI中的每个Subject都有Owner、Payload Schema和至少一个兼容性Fixture。
