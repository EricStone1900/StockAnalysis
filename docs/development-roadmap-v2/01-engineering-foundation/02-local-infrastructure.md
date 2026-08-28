# 01-02 本地基础设施与隔离

## 实施步骤

1. Docker Compose启动PostgreSQL、Temporal PostgreSQL、NATS JetStream、Redis、MinIO和OpenTelemetry Collector。
2. PostgreSQL可共用镜像实例，但每个服务创建独立Database/User；加入跨库写入拒绝测试。
3. 为NATS建立Stream、Subject命名、Durable Consumer、DLQ和重放脚本。
4. 为MinIO建立Artifact Bucket、版本和Hash元数据规范。
5. Redis只用于可丢失缓存、限流和短期锁，不保存领域事实。
6. 加入一键启动、停止、状态检查和非破坏性清理脚本。

配置只引用Secret名称：

```yaml
services:
  market-data-service:
    environment:
      DATABASE_URL_FILE: /run/secrets/market_data_db_url
```

## 测试

- 不同服务数据库用户跨库写入被拒绝。
- NATS重复投递Fixture可被消费两次。
- Temporal Worker重启后测试Workflow仍存在。
- Redis清空不丢失任何领域事实。
- MinIO Artifact Hash不匹配时读取失败。

