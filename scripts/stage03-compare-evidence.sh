#!/usr/bin/env sh
set -eu

MAC_DIR=${1:?用法: stage03-compare-evidence.sh <mac证据目录> <ubuntu证据目录>}
UBUNTU_DIR=${2:?用法: stage03-compare-evidence.sh <mac证据目录> <ubuntu证据目录>}

for name in commit.txt architecture.txt; do
  test -f "$MAC_DIR/$name" && test -f "$UBUNTU_DIR/$name"
  if ! cmp -s "$MAC_DIR/$name" "$UBUNTU_DIR/$name"; then
    if [ "$name" = architecture.txt ]; then
      echo "架构不同（允许跨平台）：$name"
    else
      echo "证据不一致：$name" >&2
      exit 1
    fi
  fi
done

echo 'Commit 证据一致；架构差异按跨平台规则单独记录。'
if [ -f "$MAC_DIR/artifact-sha256.txt" ] && [ -f "$UBUNTU_DIR/artifact-sha256.txt" ]; then
  cmp -s "$MAC_DIR/artifact-sha256.txt" "$UBUNTU_DIR/artifact-sha256.txt" || {
    echo '输入 Artifact SHA-256 不一致，验收失败' >&2
    exit 1
  }
fi
if [ -f "$MAC_DIR/canonical-content-hash.txt" ] && [ -f "$UBUNTU_DIR/canonical-content-hash.txt" ]; then
  cmp -s "$MAC_DIR/canonical-content-hash.txt" "$UBUNTU_DIR/canonical-content-hash.txt" || {
    echo 'canonicalContentHash 不一致，验收失败' >&2
    exit 1
  }
fi
