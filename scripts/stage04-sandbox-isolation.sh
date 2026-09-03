#!/usr/bin/env sh
# 阶段04真实Sandbox隔离门禁；必须在已安装Docker的Ubuntu执行。
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
image_name="${STAGE04_SANDBOX_IMAGE:-research-sandbox:fixed-v1}"
artifact_dir=$(mktemp -d)
cleanup() { rm -rf "$artifact_dir"; }
trap cleanup EXIT INT TERM

printf '%s\n' 'fixed-input' > "$artifact_dir/input.txt"
docker build --pull -t "$image_name" -f "$repository_root/services/research-automation-service/sandbox/Dockerfile" "$repository_root/services/research-automation-service/sandbox"

common_args="--network none --read-only --user 65532:65532 --cap-drop ALL --security-opt no-new-privileges --pids-limit 64 --cpus 1 --memory 512m --tmpfs /tmp:rw,noexec,nosuid,size=256m --mount type=bind,src=$artifact_dir,dst=/input,readonly"
output=$(docker run --rm $common_args "$image_name" fixed-factor-smoke-v1)
printf '%s\n' "$output" | grep -q '"scriptId": "fixed-factor-smoke-v1"'
printf '%s\n' "$output" | grep -q '"inputFileCount": 1'

if docker run --rm $common_args --entrypoint python "$image_name" -c 'import urllib.request; urllib.request.urlopen("http://example.com", timeout=2)' >/dev/null 2>&1; then
  echo 'network isolation failed' >&2
  exit 1
fi
if docker run --rm $common_args --entrypoint sh "$image_name" -c 'echo blocked >/etc/sandbox-write-test' >/dev/null 2>&1; then
  echo 'read-only filesystem isolation failed' >&2
  exit 1
fi

docker inspect "$image_name" --format '{{.Config.User}}' | grep -q '^65532:65532$'
echo 'stage04 sandbox isolation passed'
