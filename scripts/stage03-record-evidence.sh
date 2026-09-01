#!/usr/bin/env sh
set -eu

OUTPUT_DIR=${1:-artifacts/stage03/local}
mkdir -p "$OUTPUT_DIR"
umask 077

git rev-parse HEAD > "$OUTPUT_DIR/commit.txt"
git status --porcelain > "$OUTPUT_DIR/git-status.txt"
uname -a > "$OUTPUT_DIR/uname.txt"
uname -m > "$OUTPUT_DIR/architecture.txt"
python3 --version > "$OUTPUT_DIR/python-version.txt" 2>&1 || true
docker --version > "$OUTPUT_DIR/docker-version.txt" 2>&1 || true
docker compose version > "$OUTPUT_DIR/compose-version.txt" 2>&1 || true

hash_file() {
  path=$1
  output=$2
  if [ -f "$path" ]; then
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$path" > "$output"; else shasum -a 256 "$path" > "$output"; fi
  fi
}

hash_file services/quant-research-service/uv.lock "$OUTPUT_DIR/uv-lock-sha256.txt"
hash_file services/quant-research-service/migrations/001_research_metadata.sql "$OUTPUT_DIR/migration-001-sha256.txt"
hash_file services/quant-research-service/migrations/002_strategy_metadata.sql "$OUTPUT_DIR/migration-002-sha256.txt"
hash_file services/quant-research-service/migrations/003_daily_analysis.sql "$OUTPUT_DIR/migration-003-sha256.txt"
hash_file services/quant-research-service/migrations/004_strategy_runs.sql "$OUTPUT_DIR/migration-004-sha256.txt"

if command -v uv >/dev/null 2>&1 && [ -f services/quant-research-service/pyproject.toml ]; then
  (cd services/quant-research-service && UV_CACHE_DIR="${UV_CACHE_DIR:-../../.uv-cache}" uv run pytest tests/unit -o addopts='') > "$OUTPUT_DIR/unit-test.log" 2>&1 || { echo '单元测试失败，证据记录失败' >&2; exit 1; }
fi

if docker image inspect stock-analysis-infra-quant-research-service >/dev/null 2>&1; then
  docker image inspect stock-analysis-infra-quant-research-service \
    --format '{{.Id}} {{.Architecture}} {{.Os}}' > "$OUTPUT_DIR/quant-image.txt"
fi

if [ -f infra/compose/docker-compose.yml ]; then
  docker compose -f infra/compose/docker-compose.yml config --quiet
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum infra/compose/docker-compose.yml > "$OUTPUT_DIR/compose-sha256.txt"
  else
    shasum -a 256 infra/compose/docker-compose.yml > "$OUTPUT_DIR/compose-sha256.txt"
  fi
fi

echo "证据已写入 ${OUTPUT_DIR}（不包含密钥内容）"
