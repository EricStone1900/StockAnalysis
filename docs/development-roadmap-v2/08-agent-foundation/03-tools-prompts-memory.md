# 08-03 Tool、Prompt和Memory M0

## 实施步骤

1. Tool Registry登记Tool名称、输入输出Schema、调用服务、权限、超时和是否有副作用。
2. 每个Agent拥有显式允许列表；默认拒绝未登记Tool，业务数据库不作为Tool。
3. Prompt Registry保存PromptVersion、模板Hash、适用AgentVersion、状态和批准记录。
4. ContextBuilder只装配不可变SnapshotRef、EvidenceRef和freshness，计算Context Manifest/Hash。
5. Memory M0只包含当前运行事实，不检索历史经验，不使用Provider长期会话。
6. 外部新闻和第三方文本标记UNTRUSTED并与系统指令分区。

```ts
interface ToolPolicy {
  agentId: string;
  allowedTools: string[];
  maxCalls: number;
  denySideEffects: boolean;
}
```

## 测试

- 未授权Tool、参数越界、超时和恶意返回。
- Prompt注入不能改变Tool Policy。
- 相同Manifest得到相同contextHash。
- future/stale/unresolved证据被排除或阻塞。

