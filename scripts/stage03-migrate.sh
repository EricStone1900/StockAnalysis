#!/usr/bin/env sh
set -eu

COMPOSE="docker compose -f infra/compose/docker-compose.yml"
if [ -f infra/compose/docker-compose.stage03-ubuntu.yml ]; then
  COMPOSE="$COMPOSE -f infra/compose/docker-compose.stage03-ubuntu.yml"
fi

$COMPOSE exec -T postgres psql -U quant_research -d quant_research < services/quant-research-service/migrations/001_research_metadata.sql
$COMPOSE exec -T postgres psql -U quant_research -d quant_research < services/quant-research-service/migrations/002_strategy_metadata.sql
