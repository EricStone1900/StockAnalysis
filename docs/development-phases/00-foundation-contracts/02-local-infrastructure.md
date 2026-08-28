# 00-02 本地基础设施

## 目标

用Docker Compose提供按服务隔离的PostgreSQL数据库/用户、Temporal数据库、Temporal、NATS JetStream、Redis和MinIO，并保证数据卷和健康检查清晰。

## 开发边界

只建立开发基础设施，不在Compose里保存生产密钥，不把Temporal表和业务表放进同一个数据库。

## 实施步骤

### 1. 定义服务

`docker-compose.yml`核心结构：

```yaml
services:
  app-postgres:
    image: postgres:17
    environment:
      POSTGRES_DB: stock_analysis
      POSTGRES_USER: stock_app
      POSTGRES_PASSWORD: ${APP_DB_PASSWORD:-dev-only}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U stock_app -d stock_analysis"]
      interval: 5s
      timeout: 3s
      retries: 20

  temporal-postgres:
    image: postgres:17
    environment:
      POSTGRES_DB: temporal
      POSTGRES_USER: temporal
      POSTGRES_PASSWORD: ${TEMPORAL_DB_PASSWORD:-dev-only}

  redis:
    image: redis:7-alpine
    command: ["redis-server", "--appendonly", "yes"]

  nats:
    image: nats:2-alpine
    command: ["-js", "-sd", "/data"]
    volumes:
      - nats-data:/data

  minio:
    image: minio/minio
    command: server /data --console-address :9001
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-minioadmin}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-minioadmin}
```

Temporal Server可使用官方开发Compose片段，但连接`temporal-postgres`而不是业务库。

### 2. 创建服务Database和User

本地可共用一个PostgreSQL容器，但必须为每个服务建立独立Database/User。以下仅为概念示例，初始化脚本应逐一创建用户并最小授权：

```sql
CREATE DATABASE market_data OWNER market_data_app;
CREATE DATABASE quant_research OWNER quant_research_app;
CREATE DATABASE portfolio_risk OWNER portfolio_risk_app;
CREATE DATABASE decision_governance OWNER decision_governance_app;
```

其余有状态服务按同样方式创建。任何应用账户不得拥有其他服务Database的写权限。

### 3. 创建MinIO Bucket约定

- `raw-market-data`
- `research-artifacts`
- `news-raw-content`
- `model-artifacts`
- `audit-artifacts`

Bucket路径必须包含业务日期、运行ID和内容Hash，禁止依赖可变文件名覆盖历史。

### 4. 环境变量

`.env.example`只列变量名：

```dotenv
APP_DATABASE_URL=
TEMPORAL_ADDRESS=
NATS_URL=
REDIS_URL=
S3_ENDPOINT=
S3_ACCESS_KEY=
S3_SECRET_KEY=
```

真实`.env`必须在`.gitignore`中。

## 验证命令

```bash
docker compose config
docker compose up -d
docker compose ps
```

## 测试案例

1. 删除容器但保留Volume后，数据库数据仍存在。
2. Redis重启后应用能重新建立连接。
3. MinIO不可用时Readiness失败而Liveness仍可根据策略保持。
4. Temporal数据库连接失败不会污染业务数据库。
5. NATS重复投递同一测试事件时，Inbox示例Handler只产生一次业务效果。
6. 任意服务账户尝试写入其他服务Database时被拒绝。

## 完成条件

- 所有基础设施有健康检查。
- Temporal和业务PostgreSQL逻辑隔离，各业务服务Database/User隔离。
- NATS启用JetStream持久化，并有Stream、Durable Consumer和DLQ示例。
- 一条命令可启动和停止本地基础设施。
- 文档明确哪些开发凭据不可用于生产。
