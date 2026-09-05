#!/usr/bin/env bash
# Mac/Linux本地开发入口；配置校验不启动服务、不输出连接串。
set -euo pipefail
root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
action="${1:-status}"
group="${2:-infra}"
case "$action" in config|up|status) ;; *) echo '用法: bash scripts/local-stack.sh config|up|status infra|research|manual-services|full-demo' >&2; exit 2;; esac
case "$group" in
  infra) services=(postgres nats minio redis otel-collector);;
  research) services=(postgres nats minio market-data-service quant-research-service platform-api-service web);;
  # P0最小闭环不依赖Qlib/行情/Web，避免Apple Silicon构建无关服务阻塞验证。
  manual-services) services=(postgres nats portfolio-risk-service decision-governance-service trade-execution-service);;
  full-demo) services=(postgres temporal-postgres temporal nats redis minio otel-collector market-data-service quant-research-service portfolio-risk-service decision-governance-service trade-execution-service news-intelligence-service market-monitor-service market-regime-service agent-service platform-api-service web);;
  *) echo '未知本地服务组合' >&2; exit 2;;
esac
# 仅本地开发默认值；与postgres-init.sql一致。调用者显式环境设置优先。
export DECISION_GOVERNANCE_DATABASE_URL="${DECISION_GOVERNANCE_DATABASE_URL:-postgresql://decision_governance:decision_governance_local_only@postgres:5432/decision_governance}"
export TRADE_EXECUTION_DATABASE_URL="${TRADE_EXECUTION_DATABASE_URL:-postgresql://trade_execution:trade_execution_local_only@postgres:5432/trade_execution}"
export NEWS_INTELLIGENCE_DATABASE_URL="${NEWS_INTELLIGENCE_DATABASE_URL:-postgresql://news_intelligence:news_intelligence_local_only@postgres:5432/news_intelligence}"
export PORTFOLIO_INTERNAL_TOKEN="${PORTFOLIO_INTERNAL_TOKEN:-local-portfolio-internal-token}"
export GOVERNANCE_INTERNAL_TOKEN="${GOVERNANCE_INTERNAL_TOKEN:-local-governance-internal-token}"
export EXECUTION_SERVICE_TOKEN="${EXECUTION_SERVICE_TOKEN:-local-execution-service-token}"
compose=(docker compose -f "$root_dir/infra/compose/docker-compose.yml")
case "$action" in
  config) "${compose[@]}" config --quiet;;
  status) "${compose[@]}" ps "${services[@]}";;
  up)
    umask 077
    secret_dir="$root_dir/infra/compose/secrets"
    mkdir -p "$secret_dir"
    # 不覆盖已初始化数据卷使用的Secret。
    for secret_name in postgres_password temporal_postgres_password minio_root_password; do
      if [[ ! -e "$secret_dir/$secret_name" ]]; then openssl rand -hex 32 > "$secret_dir/$secret_name"; fi
    done
    echo "启动本地组合: ${group}；manual-services不表示真实授权闭环已验收，full-demo含Fake Agent。"
    "${compose[@]}" up -d --build --wait "${services[@]}"
    ;;
esac
