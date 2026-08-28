# 08-01 Agent Kernel

## 实施步骤

1. 建立AgentDefinition、AgentVersion、AgentRun、ModelRun、ToolCall和ArtifactRef。
2. 实现Runner生命周期：构建上下文、调用模型、有限Tool循环、Schema校验、保存结果。
3. Agent输出必须使用Zod Schema；解析失败只允许配置次数的修复，之后结构化失败。
4. 保存输入引用、模型元数据、PromptVersion、Tool调用、输出、错误和correlationId。
5. 先实现echo/fake-analysis Agent贯通HTTP、NATS Consumer和Temporal Activity入口。

```ts
interface AgentRunner {
  run<TInput, TOutput>(
    definition: AgentDefinition<TInput, TOutput>,
    input: TInput,
    context: AgentExecutionContext,
  ): Promise<AgentRunResult<TOutput>>;
}
```

Kernel不包含股票业务条件分支；不同Agent差异来自Definition、Schema、Prompt和Tool Policy。

## 测试

- 相同Fake模型结果解析一致。
- Tool循环、预算、超时、取消和Schema失败。
- 进程重启后AgentRun事实和Artifact不丢失。

