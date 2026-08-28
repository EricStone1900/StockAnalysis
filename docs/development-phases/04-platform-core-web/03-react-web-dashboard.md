# 04-03 React Dashboard和研究页面

## 目标

建立前后端分离页面，展示服务健康、量化快照、股票分析和人工持仓。

## 实施步骤

### 1. API Client

生成Client后封装TanStack Query：

```ts
export function useLatestResearchSnapshot() {
  return useQuery({
    queryKey: ['research', 'latest'],
    queryFn: () => api.getLatestResearchSnapshot(),
    staleTime: 60_000,
  });
}
```

审批和持仓写操作不得使用乐观更新伪造最终成功状态。

### 2. 页面

- Dashboard：服务健康、新鲜度、持仓摘要、最新研究。
- Research：候选股、持仓股、因子贡献和风险标记。
- Portfolio：现金、持仓和人工快照录入。
- Audit：按correlationId和runId查询。

### 3. Freshness组件

```tsx
function FreshnessBadge({ freshness }: { freshness: DataFreshness }) {
  return <Badge tone={freshness.isStale ? 'danger' : 'success'}>
    {freshness.isStale ? `已过期：${freshness.staleReason}` : `截至 ${freshness.asOf}`}
  </Badge>;
}
```

不得只显示“最后更新”而隐藏业务截止时间。

### 4. SSE

SSE只推送runId、事件类型和状态；收到后通过授权API重新查询详情。

## 测试案例

1. STALE快照有醒目标识。
2. API部分失败不会白屏。
3. 重复点击保存按钮只发送同一幂等键。
4. VIEWER看不到编辑和审批按钮。
5. SSE断线后可重连并重新查询状态。

## 完成条件

- 用户可完成持仓录入和研究查看。
- 页面始终展示版本与新鲜度。
- 关键页面有组件测试和浏览器E2E冒烟测试。
