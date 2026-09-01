# 03-05 Mac开发与Ubuntu交付

## 目标与交付物

阶段03采用“Mac开发验证、Ubuntu最终验收”。实现时必须提供：

- Python 3.12与完整`uv.lock`，不得使用浮动Qlib或数值依赖版本。
- 可独立构建的`quant-research-service`镜像，Ubuntu宿主端口默认使用`3001`。
- `scripts/stage03-verify-mac.sh`：Mac静态检查、单元、契约和Fixture E2E。
- `scripts/stage03-verify-ubuntu.sh`：Ubuntu迁移、集成、Qlib E2E、安全和恢复测试（完整自动化仍在后续补齐）。
- `scripts/stage03-e2e.sh`：Mac/Ubuntu均可执行的固定Fixture两次闭环烟测；真实DataVersion仍必须按Ubuntu人工验收。
- `scripts/stage03-record-evidence.sh`：输出提交、架构、镜像Digest、Compose/运行时版本、锁文件与迁移Hash以及单元测试日志。
- `scripts/stage03-compare-evidence.sh`：比较Mac与Ubuntu的Commit、输入Artifact SHA-256和`canonicalContentHash`。
- `infra/compose/docker-compose.stage03-ubuntu.yml`：使用Compose的`!override`替换基础端口列表并仅绑定`127.0.0.1`，使用Docker Secret，不暴露数据库、MinIO、NATS或API到公网。
- `scripts/stage03-server-init.sh`与`scripts/stage03-migrate.sh`：服务器 Secret 初始化和可重复数据库迁移。
- 真实数据证据：固定来源Release、归档/Manifest Hash、DataVersion、来源策略版本、质量/对账报告和许可引用。

这些脚本和Compose文件在阶段03实现期间创建；进入人工验收前必须能够按本文无交互执行。

## Mac本地门禁

1. 使用Python 3.12执行`uv sync --frozen`，确认锁文件未变化。
2. 执行Ruff、Mypy、分层Pytest以及OpenAPI/AsyncAPI契约测试。
3. 用固定Fixture DataVersion完成股票池、因子、模型基线、回测和快照最小闭环。
4. 连续运行两次，确认输入版本、规范内容Hash、排序和业务指标一致。
5. 构建Linux镜像并做启动检查；目标Ubuntu为`amd64`时，Mac必须执行`docker buildx build --platform linux/amd64`。当前锁定的`pyqlib`不提供`linux/arm64` wheel，因此Apple Silicon Docker的默认`linux/arm64`构建预期会失败，不能作为代码缺陷或Ubuntu验收结论。计算密集型验收仍在Ubuntu原生执行。

Fixture门禁通过后，再使用阶段02发布的固定真实日频DataVersion做Mac必要验证。真实归档由`market-data-service`管理，不提交Git，不通过SCP复制到源码目录；Ubuntu根据DataVersion的Artifact URI读取同一不可变输入。

## 本地 Compose 联通验证

基础Compose已包含`quant-research-service`，容器内监听3000，Mac宿主映射为3001；服务依赖健康的PostgreSQL和已启动的MinIO。
首次启动前执行：

```bash
docker compose -f infra/compose/docker-compose.yml config --quiet
docker compose -f infra/compose/docker-compose.yml build quant-research-service
docker compose -f infra/compose/docker-compose.yml up -d postgres minio quant-research-service
docker compose -f infra/compose/docker-compose.yml ps quant-research-service
curl --fail http://127.0.0.1:3001/live
curl --fail http://127.0.0.1:3001/ready
curl --fail http://127.0.0.1:3001/openapi.json -o /tmp/stage03-openapi.json
```

Apple Silicon 若上述默认构建因 `pyqlib` 不提供 `linux/arm64` wheel 而失败，使用 amd64 模拟构建并复用同一镜像名：

```bash
docker buildx build --platform linux/amd64 --load \
  -t stock-analysis-infra-quant-research-service \
  -f services/quant-research-service/Dockerfile .
docker compose -f infra/compose/docker-compose.yml up -d postgres minio quant-research-service
```

预期配置校验成功、量化服务为`running`或`healthy`，`/live`返回`UP`，`/ready`包含
`metadata_query`与`S6_ARTIFACT_MATERIALIZER`。PostgreSQL迁移必须单独执行：
`psql "$QUANT_RESEARCH_DATABASE_URL" -f services/quant-research-service/migrations/001_research_metadata.sql`。
Apple Silicon若构建Qlib的`linux/arm64`镜像失败，按本文前述规则改用Ubuntu原生或`linux/amd64`构建验证。

任一PIT、未来数据、状态门禁、幂等、Artifact Hash或契约测试失败，不得推送验收候选。

## 代码传输原则

以GitHub提交作为唯一传输方式。Mac提交并推送阶段分支，Ubuntu检出明确的Commit SHA；禁止用SCP覆盖仓库中的单个源码文件。仓库地址为`https://github.com/EricStone1900/StockAnalysis.git`。

若仓库为私有仓库，为Ubuntu配置只读GitHub Deploy Key；不得把个人密码、PAT或私钥写入仓库、Shell历史或验收记录。服务器只接收源码、锁文件、迁移、契约和Fixture，不接收`.env`、Secret、`.venv`、缓存与数据卷。

## 平台差异与可复现规则

验收记录必须保存`uname -m`、Python/Qlib/NumPy/PyArrow/LightGBM版本、线程数、随机种子和镜像Digest。固定时区为`Asia/Shanghai`，计算容器使用UTC保存时间。

- Mac原生依赖可使用`macosx universal2` wheel；容器与Ubuntu统一以`linux/amd64`验证，禁止把Mac的`.venv`复制进镜像或服务器。

- DataVersion输入Artifact的SHA-256在两端必须完全一致。
- 因子和快照的`canonicalContentHash`必须完全一致。
- Parquet与模型二进制分别校验自身SHA-256，但跨CPU只要求Schema、行数、规范内容Hash和冻结指标容差一致。
- 首版基线模型固定随机种子与线程数；超出容差直接判定`FAIL`，不得手工修改验收结果。

## 回滚

Ubuntu始终保留上一验收通过的Git Tag、镜像Digest、迁移版本和READY快照指针。代码回滚使用上一Tag重新构建或拉取已记录Digest；数据库只执行向前修复迁移，不手工删除生产式数据。新快照失败时继续提供上一READY快照并标记`isStale=true`。
