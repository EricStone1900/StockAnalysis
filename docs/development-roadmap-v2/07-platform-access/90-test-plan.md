# 阶段07测试计划

- BFF Unit/Application、生成Client Contract和真实下游Component测试。
- 认证、RBAC、审计、限流、幂等和安全Headers。
- 聚合部分失败、超时、缓存过期和Circuit Breaker。
- SSE重连、重复事件和权限变化。
- React Component、路由、状态、视觉、无障碍和错误边界。
- E2E：登录后查看数据、量化、策略、持仓、新闻、异常和Regime。
- 安全：Web无法获得内部数据库、NATS或模型Secret。

## 本机验证记录（Mac）

- contracts 的 lint、typecheck、`test:contract`：通过，生成 Client 无漂移。
- platform-api 的 lint、typecheck、unit test：通过，7 项测试。
- platform-api 的 `test:integration`：覆盖生成 Client 与 Dashboard Facade 集成契约。
- Web 的 lint、typecheck、test、build：通过，6 项测试。

集成测试使用受控 Fake Fetch，不访问真实数据库或 Provider；Ubuntu 仍需验证容器、真实 BFF 路由、安全 Headers 和下游部分失败。
