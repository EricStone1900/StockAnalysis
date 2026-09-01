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
