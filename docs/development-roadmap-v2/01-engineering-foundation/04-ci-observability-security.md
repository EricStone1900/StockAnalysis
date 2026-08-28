# 01-04 CI、观测、安全和开发体验

## 实施步骤

1. CI顺序固定为格式、lint、typecheck、unit、contract、integration、image scan。
2. 每个请求、事件和Activity传播correlationId、causationId和traceparent。
3. 统一JSON日志，禁止记录Token、数据库URL、完整Prompt、券商密钥和新闻受限正文。
4. 建立RED指标、数据库连接、NATS Lag、Outbox Lag和Temporal失败指标。
5. 配置Secret注入、依赖锁、SBOM和镜像Digest。
6. 建立开发Fixture、Testcontainer和CI缓存规范。

## 测试

- 一个HTTP请求跨Fake事件链保持同一correlationId。
- 日志扫描Fixture中的Secret不会输出。
- Readiness依赖故障返回DOWN，Liveness仍为UP。
- 漏洞扫描高危项阻止发布。

