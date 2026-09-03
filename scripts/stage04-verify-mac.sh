#!/usr/bin/env sh
# 阶段04本地门禁：运行研究服务静态、单元及无数据库集成测试。
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
service_directory="$repository_root/services/research-automation-service"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$repository_root/.uv-cache}"

cd "$service_directory"
uv sync --frozen --group dev
uv run ruff check .
uv run mypy src
uv run pytest tests/unit tests/integration -o addopts=''
