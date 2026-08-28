# 07-01 Platform API

## 实施步骤

1. 从Node模板实现认证Principal、RBAC、Request Audit和Problem Details。
2. 只使用阶段02～06生成的OpenAPI Client，按页面建立Query Facade。
3. 第一个纵向切片为“查询最新DataVersion、DailyAnalysisSnapshot和服务健康摘要”。
4. 聚合响应为每个下游声明freshness和dependencyStatus；部分依赖失败不伪造空数据。
5. 写命令只做代理：保留actor、幂等键和correlationId，不在BFF本地改变领域状态。

```ts
interface PartialResult<T> {
  data?: T;
  status: 'OK' | 'STALE' | 'UNAVAILABLE' | 'FORBIDDEN';
  asOf?: string;
  errorCode?: string;
}
```

## 测试

- 生成Client契约漂移阻止构建。
- 单个下游超时返回部分结果。
- 未授权用户不能调用写代理。
- BFF数据库中不存在领域事实表。

