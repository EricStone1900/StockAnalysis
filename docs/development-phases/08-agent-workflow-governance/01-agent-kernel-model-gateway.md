# 08-01 Agent Kernel和多模型网关

## 目标

在独立`services/agent-service`中实现厂商无关的TypeScript Agent Kernel、Provider Adapter、Tool白名单、结构化输出和完整审计，并用同一镜像配置出六个独立Agent部署。

## 实施步骤

### 1. AgentDefinition

```ts
export interface AgentDefinition<I, O> {
  agentId: string;
  agentVersion: string;
  promptVersion: string;
  modelProfile: ModelProfile;
  inputSchema: z.ZodType<I>;
  outputSchema: z.ZodType<O>;
  allowedTools: readonly string[];
  limits: {
    timeoutMs: number;
    maxToolCalls: number;
    maxOutputTokens: number;
  };
}
```

Agent定义不能包含真实API Key或直接构造HTTP Client。

进程启动时必须读取`AGENT_ID`并只加载一个AgentDefinition；若配置缺失、Tool权限超集或Task Queue不匹配，Readiness失败。

### 2. Provider Adapter

```ts
export interface ModelProvider {
  readonly providerId: string;
  capabilities(): ModelCapabilities;
  generate<T>(request: ModelRequest<T>): Promise<ModelResponse<T>>;
}
```

实现：

- `GenericOpenAICompatibleProvider`：DeepSeek及其他OpenAI格式模型。
- `AnthropicProvider`：Claude原生接口。
- `OpenAIProvider`：需要厂商专有能力时使用。
- `FakeProvider`：测试固定输出、超时和错误。

### 3. ModelRouter

```ts
const route = router.resolve({
  profile: 'risk-review',
  required: ['structuredOutput'],
  excludedProviders: failedProviders,
});
```

路由配置是发布版本。切换Provider生成新modelRunId，记录原模型、备用模型和原因。

### 4. Tool Registry

```ts
registry.register({
  name: 'getDailyAnalysisSnapshot',
  inputSchema,
  outputSchema,
  execute: researchClient.getSnapshot,
  permission: 'research:read',
});
```

运行前取Agent白名单与服务端权限交集；不存在的Tool或越权调用立即失败。

### 5. Runner

```ts
async function runAgent<I, O>(definition: AgentDefinition<I, O>, input: I): Promise<O> {
  const validInput = definition.inputSchema.parse(input);
  const context = await contextBuilder.build(definition, validInput);
  const response = await modelRouter.generate(definition.modelProfile, context);
  const output = definition.outputSchema.parse(response.output);
  await evidenceValidator.assertResolvable(output);
  await auditRecorder.record(definition, response, output);
  return output;
}
```

实际实现使用AbortSignal、预算、重试分类和Artifact存储。

## 测试案例

1. DeepSeek换成Fake Provider不修改Agent定义。
2. Provider不支持structuredOutput时路由拒绝。
3. Agent调用未授权Tool失败并审计。
4. 输出Schema错误不会传给业务层。
5. 主Provider超时切备用且modelRunId不同。
6. 所有Provider失败返回可识别错误，不返回猜测结果。
7. 同一镜像以六个`AGENT_ID`启动时只订阅各自Durable Consumer和Task Queue。

## 完成条件

- Kernel模块不依赖具体业务Agent。
- 所有调用有Agent/Prompt/Model版本。
- Tool权限、Token和超时限制生效。
- Fake Provider可稳定运行Golden测试。
- 停止financial-news-agent不会停止main-decision-agent或risk-review-agent。
