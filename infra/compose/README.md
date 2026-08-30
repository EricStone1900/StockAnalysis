# 本地基础设施

运行 `../../scripts/infra-up.sh` 启动 PostgreSQL、Temporal、NATS JetStream、Redis、MinIO 和 OTel。脚本只创建被 `.gitignore` 忽略的本地开发 Secret 文件；不得将其提交。

PostgreSQL 为每个服务创建独立 Database/User。服务凭证在阶段 01-03 通过 Secret 文件引用；禁止跨库连接或共享表。Redis 仅用于可丢失缓存、限流和短期锁，不能保存领域事实。MinIO Artifact 必须保存内容 Hash 与版本元数据。
