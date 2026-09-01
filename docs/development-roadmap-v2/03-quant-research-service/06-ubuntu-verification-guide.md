# 阶段03 Ubuntu 完整验证手册

本文用于在 Ubuntu 服务器上独立完成阶段03验证。所有标记“服务器端”的命令必须在 SSH 会话中执行；Mac 只负责准备 Commit 和复制证据。当前仓库已提供 Mac 验证脚本、Ubuntu Compose 覆盖文件、Secret 初始化脚本、迁移脚本和 Ubuntu 基础自动化脚本；真实 DataVersion、故障恢复与回滚仍需按本文人工执行。

## 1. 验证前提与变量

在 Mac 设置变量并替换实际值：

```bash
export UBUNTU_USER='SSH用户名'
export UBUNTU_HOST='服务器IP或域名'
export STAGE03_DIR='/opt/stock-analysis'
export STAGE03_BRANCH='stage/03-quant-research'
export STAGE03_COMMIT='待验收Commit的完整SHA'
export STAGE03_DATA_VERSION='阶段02发布的DataVersion'
export STAGE03_SOURCE_RELEASE='investment_data固定Release Tag'
```

不得把密码、Token、私钥或真实数据写入仓库、命令历史或本文档。

## 2. 检查 Ubuntu 环境（服务器端）

```bash
uname -a; uname -m; nproc; free -h; df -h /
docker --version; docker compose version; git --version
timedatectl status
```

预期 Docker Engine、Compose Plugin、Git 均可用；记录架构（通常为 `x86_64`）、CPU、内存、磁盘和时区。防火墙只允许 SSH，禁止公网访问 3001、5433、4222、9000、9001、8222。

## 3. 获取并固定代码（服务器端）

```bash
sudo install -d -o "$(id -un)" -g "$(id -gn)" "$STAGE03_DIR"
git clone --branch "$STAGE03_BRANCH" https://github.com/EricStone1900/StockAnalysis.git "$STAGE03_DIR"
cd "$STAGE03_DIR"
git fetch origin "$STAGE03_BRANCH"
git switch --detach "$STAGE03_COMMIT"
test "$(git rev-parse HEAD)" = "$STAGE03_COMMIT"
test -z "$(git status --porcelain)"
```

若仓库为私有仓库，使用只读 Deploy Key。SHA 不一致或工作区不干净时立即停止。

## 4. 配置与端口安全（服务器端）

先检查所需文件：

```bash
test -f infra/compose/docker-compose.yml
test -f services/quant-research-service/migrations/001_research_metadata.sql
```

当前基础 Compose 适合本地开发。正式 Ubuntu 验收前，应使用阶段03专用 override，将所有端口绑定到 `127.0.0.1`，并用 Docker Secret 提供密码。生成配置后检查：

```bash
docker compose -f infra/compose/docker-compose.yml config > /tmp/stage03-compose.yml
if grep -n '0.0.0.0' /tmp/stage03-compose.yml; then
  echo '发现公网端口映射，停止验收'; exit 1
fi
```

不得直接复用 Mac 的 `.env`、`.venv`、缓存或数据卷。

## 5. 构建并启动（服务器端）

```bash
docker compose -f infra/compose/docker-compose.yml build --pull quant-research-service
docker compose -f infra/compose/docker-compose.yml up -d postgres minio quant-research-service
docker compose -f infra/compose/docker-compose.yml ps
docker image inspect stock-analysis-infra-quant-research-service \
  --format '{{.Id}} {{.Architecture}} {{.Os}}'
```

服务应为 `running` 或 `healthy`，镜像架构应与 `uname -m` 匹配。Ubuntu 不得依赖 Mac 构建的镜像。

## 6. 迁移与 API 检查（服务器端）

```bash
docker compose -f infra/compose/docker-compose.yml exec -T postgres \
  psql -U quant_research -d quant_research \
  < services/quant-research-service/migrations/001_research_metadata.sql
docker compose -f infra/compose/docker-compose.yml exec -T postgres \
  psql -U quant_research -d quant_research \
  < services/quant-research-service/migrations/001_research_metadata.sql
curl --fail http://127.0.0.1:3001/live
curl --fail http://127.0.0.1:3001/ready
curl --fail http://127.0.0.1:3001/openapi.json -o /tmp/stage03-openapi.json
```

两次迁移都必须成功且无重复对象错误；健康响应为 `UP`。人工检查 OpenAPI 仅包含研究元数据只读查询，不包含交易、审批或订单写接口。

## 7. 自动化质量门禁（服务器端）

先执行基础自动化入口：

```bash
./scripts/stage03-verify-ubuntu.sh
```

脚本完成 Compose 安全检查、原生构建、启动、双次迁移、健康/API 检查和可用时的 Python 质量检查。脚本通过不等于完成真实数据与故障恢复验收，必须继续执行后续章节。

```bash
cd services/quant-research-service
uv sync --frozen
uv run ruff check .
uv run mypy src
uv run pytest tests/unit -o addopts=''
MARKET_DATA_DATABASE_URL='postgresql://quant_research:<服务器Secret>@localhost:5433/quant_research' \
  uv run pytest tests/integration -o addopts=''
cd ../..
git diff --check
```

所有检查必须通过；任何 PIT、未来数据、幂等、Hash 或数据库集成失败均为 `FAIL`。保存完整终端日志和退出码。

## 8. 真实 DataVersion 验收（服务器端）

核对阶段02固定的 `investment_data` Release、归档 SHA-256、Manifest、DataVersion、来源策略版本、日期范围、证券数、行数、缺失率、补充率、冲突率和许可信息。确认输入 Artifact SHA-256 与 Mac 证据一致；不得使用 `latest` 或让服务直接访问第三方数据源。

先启用价格动量、波动率、流动性因子完成两次重复运行。确认两次的 UniverseVersion、FactorSetVersion、ModelVersion、随机种子、排序和 `canonicalContentHash` 一致；只有 `ACTIVE` 版本进入快照，`DRAFT/CANDIDATE` 必须被拒绝。若使用 `assume_suspension_on_read`，保留 `WARN` 结论、策略 Artifact URI/Hash 和抽样停牌证据，不得签署为正式 `PASS`。

## 9. 故障、恢复与资源隔离（服务器端）

逐项人工注入并记录结果：错误 Artifact Hash、未来数据、重复事件、部分计算、PostgreSQL/MinIO/NATS 不可用、任务超时/OOM、Runner 外网访问。预期均不能发布 READY；重复事件只产生一个 Run；恢复后 Outbox 只补发一次；失败时上一 READY 快照仍可查询并标记 `isStale=true`；Runner 无法访问外网、数据库、宿主写目录或生产 Secret。

## 10. 证据比对、回滚与签署

在 Mac 导出本地证据后复制到服务器：

```bash
scp -r artifacts/stage03/mac "$UBUNTU_USER@$UBUNTU_HOST:/tmp/stage03-mac-evidence"
```

服务器端比较 Commit SHA、输入 Artifact SHA-256、契约版本、规范内容 Hash、快照行数和冻结指标。任何 Hash、PIT 或指标超出容差均为 `FAIL`。最后保留上一通过 Tag、镜像 Digest、迁移版本和 READY 快照，演练恢复并确认 API 返回旧快照。验收记录必须填写 Commit、镜像、架构、依赖版本、DataVersion、测试报告、风险、回滚目标、时间和签署人。

完成第1～10节且所有硬门禁通过后，才可将阶段03标记为 `PASS`；否则记录失败项、日志路径和修复 Commit，不得跳过 Ubuntu 验证。
