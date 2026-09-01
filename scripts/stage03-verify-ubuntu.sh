#!/usr/bin/env sh
set -eu

BASE='docker compose -f infra/compose/docker-compose.yml'
OVERRIDE='infra/compose/docker-compose.stage03-ubuntu.yml'
if [ -f "$OVERRIDE" ]; then
  BASE="$BASE -f $OVERRIDE"
fi

echo '[1/7] 校验 Compose 配置与端口安全'
$BASE config > /tmp/stage03-compose-ubuntu.yml
if grep -q '0.0.0.0' /tmp/stage03-compose-ubuntu.yml; then
  echo '发现公网端口映射，验证失败' >&2
  exit 1
fi

echo '[2/7] 构建量化研究服务（服务器原生架构）'
$BASE build --pull quant-research-service

echo '[3/7] 启动依赖和量化服务'
$BASE up -d postgres minio quant-research-service
$BASE ps

echo '[4/7] 执行可重复迁移'
./scripts/stage03-migrate.sh
./scripts/stage03-migrate.sh

echo '[5/7] 健康和 OpenAPI 检查'
curl --fail http://127.0.0.1:3001/live
curl --fail http://127.0.0.1:3001/ready
curl --fail http://127.0.0.1:3001/openapi.json -o /tmp/stage03-openapi.json
grep -q '/api/v1/strategy-runs/{run_id}' /tmp/stage03-openapi.json
grep -q '/api/v1/strategy-snapshots/{snapshot_id}' /tmp/stage03-openapi.json

echo '[6/7] 镜像架构记录'
docker image inspect stock-analysis-infra-quant-research-service --format '{{.Id}} {{.Architecture}} {{.Os}}'

echo '[7/7] 可选 Python 质量检查'
if command -v uv >/dev/null 2>&1; then
  (cd services/quant-research-service && uv sync --frozen && uv run ruff check . && uv run mypy src && uv run pytest tests/unit -o addopts='')
else
  echo '未安装 uv，跳过 Python 质量检查；请按 Ubuntu 手册安装后重跑。'
fi

echo '阶段03 Ubuntu 基础自动化检查通过；真实数据、故障恢复和回滚仍需人工验收。'
