# 阶段04 Ubuntu验证手册

本文用于在新的 Ubuntu 服务器上验证阶段04当前已实现的代码。所有命令均在 SSH 登录后的 Ubuntu 终端执行，Mac 只负责推送代码。当前最新验证候选 Commit 为 `d54c436`；如果远端已有更新，应使用实际固定 SHA 替换本文中的值。

## 1. 准备与安全边界

在 Mac 确认代码已推送：

```bash
git fetch origin main
git rev-parse origin/main
```

在 Ubuntu 安装并检查 Git、Docker Engine、Compose Plugin、Buildx、Python 3.12/3.13 和 `uv`：

```bash
uname -a
uname -m
docker --version
docker compose version
git --version
python3 --version
uv --version
```

记录 CPU 架构、内存、磁盘和时区。防火墙只开放 SSH，不对公网开放 PostgreSQL、MinIO、NATS 或研究服务端口。不要复制 Mac 的 `.venv`、缓存、Docker 数据卷、`.env` 或任何密钥。

## 2. 拉取固定代码

```bash
export STOCK_ROOT=/opt/stock-analysis
export STAGE04_COMMIT=d54c436
git clone https://github.com/EricStone1900/StockAnalysis.git "$STOCK_ROOT"
cd "$STOCK_ROOT"
git fetch origin main
git checkout --detach "$STAGE04_COMMIT"
test "$(git rev-parse HEAD)" = "$(git rev-parse "$STAGE04_COMMIT")"
git status --porcelain
```

最后一条必须无输出。固定 Commit 是为了让代码、锁文件和迁移版本可追溯，禁止使用浮动分支或 `latest` 镜像作为验收输入。

## 3. 安装研究服务依赖

```bash
cd "$STOCK_ROOT/services/research-automation-service"
export UV_CACHE_DIR="$STOCK_ROOT/.uv-cache"
uv sync --frozen --group dev
```

`--frozen` 强制使用仓库中的 `uv.lock`，避免 Ubuntu 解析出与 Mac 不同的依赖版本。检查 `pyproject.toml`、`uv.lock` 和 Python 主版本一致。

## 4. Mac/Ubuntu通用自动检查

```bash
cd "$STOCK_ROOT"
./scripts/stage04-verify-mac.sh
```

该脚本会运行 Ruff、Mypy、单元测试和集成测试。未设置 `RESEARCH_AUTOMATION_DATABASE_URL` 时，3 个 PostgreSQL 测试显示 `skipped` 是预期现象，不得把它们记为数据库通过。

预期当前结果：24 个测试通过，3 个数据库测试等待数据库配置。若 Ruff、Mypy 或任一单元测试失败，立即停止并记录日志。

## 5. 准备测试 PostgreSQL

使用独立测试库，不要使用生产数据库。若已有 PostgreSQL 容器，先确认端口和用户：

```bash
docker ps
docker port <postgres容器名>
```

设置连接串（密码只存在当前 Shell，不写入仓库）：

```bash
export RESEARCH_AUTOMATION_DATABASE_URL='postgresql://research_automation:<测试密码>@127.0.0.1:5433/research_automation_test'
```

如测试库不存在，由管理员创建后再继续。执行研究服务迁移：

```bash
cd "$STOCK_ROOT/services/research-automation-service"
uv run python -c "from pathlib import Path; from src.research_automation.persistence import PostgresExperimentRepository; r=PostgresExperimentRepository(__import__('os').environ['RESEARCH_AUTOMATION_DATABASE_URL']); r.migrate(Path('migrations/001_research_automation.sql')); r.migrate(Path('migrations/002_promotion_governance.sql'))"
```

迁移重复执行必须成功；这是验证迁移幂等和服务器重启恢复能力。检查表：

```bash
psql "$RESEARCH_AUTOMATION_DATABASE_URL" -c '\dt research_*'
```

## 6. PostgreSQL集成测试

```bash
cd "$STOCK_ROOT/services/research-automation-service"
uv run pytest tests/integration -o addopts=''
```

预期 3 个集成测试全部通过，覆盖实验持久化、实验幂等、Outbox 幂等和 PromotionRequest 审计。然后重复执行一次，确认同一测试数据不会因重复迁移或重复请求产生冲突。

## 7. 真实MinIO/S3 Artifact验证

准备只允许研究 Artifact Bucket 的 MinIO Endpoint、Access Key 和 Secret；不要把 Secret 写入命令历史或文件。设置：

```bash
export RESEARCH_ARTIFACT_ENDPOINT='http://127.0.0.1:9000'
export RESEARCH_ARTIFACT_BUCKET='artifacts'
export RESEARCH_ARTIFACT_ACCESS_KEY='<只读/写入Artifact专用账号>'
export RESEARCH_ARTIFACT_SECRET_KEY='<通过Secret管理器注入>'
```

人工确认 Bucket 不允许访问生产数据库、账户数据或任意公网对象。使用 `S3ArtifactStore` 验证以下结果：

1. 正确 SHA-256 的对象首次写入成功。
2. 同一 URI、同一内容重复写入成功且不产生第二个版本。
3. 同一 URI、不同内容写入失败。
4. 读取时 Hash 不一致失败。
5. 不存在对象、路径逃逸或非对象存储 URI 失败。

Artifact 只保存 URI、Hash 和 Manifest，不把代码、大日志或密钥写入事件与数据库。

## 8. Provider、Manifest与Promotion契约

```bash
cd "$STOCK_ROOT/services/research-automation-service"
uv run pytest tests/unit/test_provider.py tests/unit/test_reproducibility.py tests/unit/test_promotion.py tests/unit/test_quant_contract.py -o addopts=''
```

人工确认：非法 JSON、额外字段、缺少支持证据/反例/失败原因、超大响应、负 Token/成本和 Hash 篡改均失败关闭；模型调用审计仍被保留；候选只能进入 `PromotionRequest`，不能进入生产 Registry。

## 9. Sandbox隔离验证

检查 `FixedScriptSandbox` 构造的命令必须包含：`--network none`、`--read-only`、非 root 用户、`--cap-drop ALL`、`no-new-privileges`、CPU/内存/PID 上限、受限 `/tmp` 和只读 Artifact 挂载。

执行阶段04提供的真实镜像和隔离脚本：

```bash
cd "$STOCK_ROOT"
./scripts/stage04-sandbox-isolation.sh
```

脚本会原生构建 `research-sandbox:fixed-v1`，以固定输入执行白名单脚本，并验证无网络、只读根目录和非 root 用户。Docker Socket、生产 Secret、宿主写目录、超时、OOM、Fork Bomb 和日志上限仍应由运维人员按服务器运行时策略抽样确认；任一项失败都不能签署 PASS。

## 10. 研究服务不影响量化生产

确认研究服务使用独立数据库用户和独立网络身份，不能连接或写入 quant 数据库。使用研究身份请求生产激活接口时，必须返回 403 或等价拒绝；研究服务停止后，阶段03的 DailyAnalysis/DailyStrategy 查询仍应可用。

## 11. 验收记录与结论

保存以下摘要：Commit SHA、Ubuntu 架构、Python/uv 版本、迁移版本、Artifact Bucket、输入/输出 Hash、测试命令及结果、隔离检查结果、失败场景、回滚目标和验收时间。不得保存 Secret、原始数据或完整密钥文件。

只有 PostgreSQL、真实 MinIO、Sandbox 实际容器隔离、跨服务权限和故障恢复全部通过，才能在 `99-acceptance.md` 标记阶段04为 `PASS`。若仅完成本文第 1～8 节，应记录为“代码与契约通过，生产隔离待验收”。
