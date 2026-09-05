# 00-07 共享语义与契约草案

## 基础值对象与时间

| 概念 | 基线规则 | 拒绝条件 |
|---|---|---|
| `SecurityId` | 由 market-data-service 分配的稳定主键；展示代码与交易所代码是属性，不得作为跨服务主键 | 缺失稳定主键或代码无法解析 |
| Decimal | 金额、价格、数量、费率以 Decimal 语义计算；JSON 使用字符串并由字段协议说明精度 | JSON number、NaN、Infinity、未声明精度 |
| 业务时区 | 交易日、开闭市和日频切点按 `Asia/Shanghai` 解释；持久化时间一律 UTC ISO-8601 | 无时区时间、错误交易日历 |
| `DataVersion` | 表示可重建的数据快照版本，必须关联来源、覆盖范围、质量结论和发布时刻 | 不可追溯或质量 FAIL 的版本进入生产 |
| `availableAt` | 数据在系统可合法使用的最早 UTC 时刻；回放 R 仅可读 `availableAt <= R` | 用 `occurredAt` 代替可见时间、读取未来数据 |

## 命令、错误与事件

所有改变领域事实的命令必须携带 `Idempotency-Key`、`actorId`、`correlationId` 与 `expectedVersion`。重复幂等键返回首次处理的结果；版本不符返回 `CONFLICT`；未授权 actor 返回权限错误。内部服务只能透传已验证的身份声明。

```ts
// 此处只引用生成类型，不手工维护第二份Envelope。
import type { DomainEventEnvelope } from '@stock/contracts';
```

事件 Payload 只放业务必要字段、不可变快照 ID 或 Artifact URI/Hash；新闻全文、Tick 流、因子矩阵和模型二进制禁止进入消息。Minor 版本仅允许兼容增加；字段语义删除、收紧或变更必须升 Subject Major，并保留迁移期。

```ts
interface ErrorEnvelope {
  code: string;
  message: string;
  retryable: boolean;
  category: 'VALIDATION' | 'NOT_FOUND' | 'CONFLICT' | 'DATA_QUALITY' |
    'DEPENDENCY' | 'RATE_LIMIT' | 'TIMEOUT' | 'INTERNAL';
  correlationId: string;
}
```

错误消息不得包含密钥、SQL、模型私密输入或供应商凭证。每个投资决策输入必须有 Freshness 与 Provenance 或不可变快照引用；过期、来源缺失或未来可见的数据必须阻断自动推进并暴露原因。

## 阶段 01 落地约束

阶段 01 在 `packages/contracts/openapi/`、`packages/contracts/asyncapi/`、`packages/contracts/schemas/` 建立可执行 Schema 与生成器，生成 TypeScript/Python 类型。阶段 00 的本文件是语义基线，不替代后续的机器可读契约。
