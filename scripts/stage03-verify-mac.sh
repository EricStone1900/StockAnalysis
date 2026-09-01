#!/usr/bin/env sh
# 阶段03的本机基础门禁；完整 Qlib、回测与组件验收仍在后续步骤完成。
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
service_directory="$repository_root/services/quant-research-service"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$repository_root/.uv-cache}"

cd "$service_directory"
uv sync --frozen --group dev
uv run ruff check .
uv run mypy src
uv run pytest tests/unit -o addopts=''
