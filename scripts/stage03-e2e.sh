#!/usr/bin/env sh
set -eu

REPEAT=2
while [ "$#" -gt 0 ]; do
  case "$1" in
    --repeat) REPEAT=$2; shift 2 ;;
    --data-version|--source-release) shift 2 ;;
    *) echo "未知参数: $1" >&2; exit 64 ;;
  esac
done
[ "$REPEAT" -ge 2 ] || { echo '--repeat 至少为2' >&2; exit 64; }
cd "$(CDPATH= cd -- "$(dirname -- "$0")/../services/quant-research-service" && pwd)"
UV_CACHE_DIR="${UV_CACHE_DIR:-../../.uv-cache}" uv run pytest tests/unit/test_stage03_e2e.py -o addopts=''
