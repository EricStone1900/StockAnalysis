#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
secret_dir="$root_dir/infra/compose/secrets"
mkdir -p "$secret_dir"
printf '%s' 'local-postgres-password' > "$secret_dir/postgres_password"
printf '%s' 'local-temporal-password' > "$secret_dir/temporal_postgres_password"
printf '%s' 'local-minio-password' > "$secret_dir/minio_root_password"
docker compose -f "$root_dir/infra/compose/docker-compose.yml" up -d
