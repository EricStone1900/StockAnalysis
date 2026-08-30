SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', name, name || '_local_only')
FROM unnest(ARRAY[
  'market_data', 'quant_research', 'research_automation', 'news_intelligence',
  'market_monitor', 'market_regime', 'portfolio_risk', 'decision_governance',
  'trade_execution', 'platform_api', 'workflow_orchestration', 'agent_runtime'
]) AS name \gexec

SELECT format('CREATE DATABASE %I OWNER %I', name, name)
FROM unnest(ARRAY[
  'market_data', 'quant_research', 'research_automation', 'news_intelligence',
  'market_monitor', 'market_regime', 'portfolio_risk', 'decision_governance',
  'trade_execution', 'platform_api', 'workflow_orchestration', 'agent_runtime'
]) AS name \gexec
