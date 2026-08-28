# 阶段03：quant-research-service

## 目标

独立交付可复现的Qlib量化生产服务：股票池、因子、模型、回测、DailyAnalysisSnapshot和可扩展DailyStrategySnapshot。

领域基线见[量化服务](../../architecture/services/quant-research-service.md)与[日频策略平台](../../architecture/services/daily-strategy-extension-design.md)。

## 顺序

1. [Qlib数据集、股票池与Factor Registry](./01-qlib-universe-factor.md)。
2. [评估、模型和回测](./02-evaluation-model-backtest.md)。
3. [每日分析快照](./03-daily-analysis-production.md)。
4. [策略Registry与Plugin SDK](./04-daily-strategy-platform.md)。
5. [测试](./90-test-plan.md)与[验收](./99-acceptance.md)。

## 边界

只输出量化事实、候选组合和策略快照，不生成TradeProposal、Approval或Order。Agent和Workflow尚未接入，全部调用用Fixture/Fake Consumer验证。

