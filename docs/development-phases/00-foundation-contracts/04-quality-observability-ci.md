# 00-04 质量、可观测性与CI

## 目标

在业务开发前统一错误、日志、Tracing、Metrics和CI门禁。

## 实施步骤

### 1. 请求上下文

Node AsyncLocalStorage保存：

```ts
export interface RequestContext {
  requestId: string;
  correlationId: string;
  actorId?: string;
  sourceService: string;
}
```

HTTP入口生成或校验ID，调用内部服务和Temporal Activity时继续传递。

### 2. 结构化日志

```ts
logger.info({
  event: 'job.accepted',
  runId,
  correlationId,
  jobType,
});
```

禁止字符串拼接密钥、完整Prompt、新闻全文和券商响应。

### 3. 健康和版本

所有HTTP服务实现：

```text
GET /health/live
GET /health/ready
GET /metrics
GET /internal/v1/version
```

`ready`检查必须区分必要依赖和可降级依赖。版本响应包含gitCommit、buildTime和contractVersion。

### 4. CI门禁

建议流水线顺序：

```yaml
steps:
  - install locked dependencies
  - validate and regenerate contracts
  - lint
  - typecheck
  - unit tests
  - contract tests
  - build images
  - dependency and secret scan
```

### 5. 最小Metrics

- HTTP请求数、延迟、错误率。
- 数据库连接池。
- Worker任务成功/失败/重试。
- dependency health。

## 测试案例

1. 请求跨两个服务后correlationId不变。
2. 缺失requestId时服务端生成新ID。
3. 数据库断开时`ready`失败、`live`保持可用。
4. 日志扫描不出现测试密钥。
5. 故意修改生成类型后CI失败。

## 完成条件

- 所有空服务使用同一观测包。
- CI在干净环境完整通过。
- 错误返回统一ErrorEnvelope。
- 每次构建可以追溯代码和契约版本。
