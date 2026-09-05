#!/usr/bin/env bash
set -euo pipefail
root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root_dir"
: "${TRADE_EXECUTION_DATABASE_URL:?请设置隔离测试PostgreSQL连接；不得将跳过集成测试视为通过}"
: "${PORTFOLIO_DATABASE_URL:?请设置隔离测试PostgreSQL连接；不得将跳过集成测试视为通过}"
pnpm --filter @stock/trade-execution-service lint
pnpm --filter @stock/trade-execution-service typecheck
pnpm --filter @stock/trade-execution-service exec vitest run tests/unit tests/integration/execution-transaction.spec.ts
pnpm --filter @stock/workflow-orchestration-service lint
pnpm --filter @stock/workflow-orchestration-service typecheck
pnpm --filter @stock/workflow-orchestration-service test
pnpm --filter @stock/contracts test:contract
pnpm --filter @stock/portfolio-risk-service lint
pnpm --filter @stock/portfolio-risk-service typecheck
pnpm --filter @stock/portfolio-risk-service exec vitest run tests/unit/resource-reservation.spec.ts tests/integration/resource-reservation.spec.ts
git diff --check
echo '执行整改专项门禁通过；不代表真实服务E2E或生产发布通过。'
