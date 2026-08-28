# 10-01 Temporal骨架与Activity

## 实施步骤

1. 建立Workflow/Activity目录、Task Queue、Worker、Schedule和版本策略。
2. 每个Activity只调用一个明确服务Use Case，接收workflowId、runId、correlationId和Idempotency-Key。
3. 错误分类为Retryable、NonRetryable、Blocked和Cancelled；写操作依靠服务端幂等。
4. 查询大对象只返回引用；Tick、新闻正文、Prompt全文和回测结果不进入History。
5. 建立Fake Activity测试和Temporal Time Skipping测试。

```ts
interface ActivityRequest<T> {
  workflowId: string;
  runId: string;
  correlationId: string;
  idempotencyKey: string;
  payload: T;
}
```

## 测试

- Worker重启、Activity超时、重试和取消。
- 相同Activity重放不产生重复写入。
- Workflow确定性和安全升级测试。

