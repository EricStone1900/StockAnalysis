#!/usr/bin/env sh
set -eu

case "${1:-}" in
  future-data|bad-artifact-hash|duplicate-event|partial-calculation|nats-outage|runner-isolation)
    TEST_NAME=test_future_data_is_rejected_by_strategy_context
    [ "$1" = bad-artifact-hash ] && TEST_NAME=test_bad_artifact_hash_is_rejected
    [ "$1" = duplicate-event ] && TEST_NAME=test_duplicate_event_conflict_is_rejected
    [ "$1" = partial-calculation ] && TEST_NAME=test_partial_calculation_cannot_use_failed_input
    if [ "$1" = nats-outage ]; then TEST_NAME=test_outbox_failure_keeps_event_pending; fi
    if [ "$1" = runner-isolation ]; then TEST_NAME=test_untrusted_runner_isolation_is_enforced; fi
    cd "$(CDPATH= cd -- "$(dirname -- "$0")/../services/quant-research-service" && pwd)"
    UV_CACHE_DIR="${UV_CACHE_DIR:-../../.uv-cache}" exec uv run pytest "tests/unit/test_stage03_failures.py::$TEST_NAME" -o addopts=''
    ;;
  *)
    echo "用法: $0 {future-data|bad-artifact-hash|duplicate-event|partial-calculation|nats-outage|runner-isolation}" >&2
    exit 64
    ;;
esac
