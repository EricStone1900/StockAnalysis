# 08-02 多模型网关

## 实施步骤

1. 定义Provider Port，业务Agent只使用逻辑ModelProfile，不引用DeepSeek/Claude SDK。
2. 实现DeepSeek和通用OpenAI兼容Adapter；再实现Anthropic Adapter。
3. 建立能力矩阵：结构化输出、Tool Calling、Context长度、超时、成本和地区策略。
4. 路由根据Agent Profile选择主Provider、备用Provider和推理参数；切换产生新modelRunId。
5. 实现Token/成本预算、并发、限流、超时、重试和Circuit Breaker。

```ts
interface ModelProvider {
  invoke(request: CanonicalModelRequest): Promise<CanonicalModelResponse>;
  capabilities(): ModelCapabilities;
}
```

Provider Conversation不作为长期Memory；输入输出转换保持规范化并保存Hash。

## 测试

- DeepSeek/OpenAI兼容/Claude Fixture通过同一契约。
- Tool能力不支持时路由拒绝或选备用模型。
- 超时、429、无效JSON、成本超限和全部Provider失败。

