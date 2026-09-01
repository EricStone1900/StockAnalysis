#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SECRET_DIR="$ROOT_DIR/infra/compose/secrets"
umask 077
mkdir -p "$SECRET_DIR"
chmod 700 "$SECRET_DIR"

create_secret() {
  name=$1
  path="$SECRET_DIR/$name"
  if [ ! -s "$path" ]; then
    if command -v openssl >/dev/null 2>&1; then
      openssl rand -base64 32 | tr -d '\n' > "$path"
    else
      head -c 32 /dev/urandom | base64 | tr -d '\n' > "$path"
    fi
  fi
  chmod 600 "$path"
}

create_secret postgres_password
create_secret temporal_postgres_password
create_secret minio_root_password
echo "Docker Secret 文件已就绪（仅输出路径，不输出内容）：$SECRET_DIR"
