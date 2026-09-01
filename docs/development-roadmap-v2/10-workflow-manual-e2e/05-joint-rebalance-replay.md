# 10-05 日频与盘中组合调仓联合回放

## 目标

使用当时可见的日频快照和历史分钟数据，联合回放日频目标组合、盘中异常、Regime、组合级RiskEvaluation、每日0～2批预算、人工决策规则和A股执行约束，验证盘中层在成本后是否优于纯日频基线。

本回放是进入阶段12 Paper/Shadow的门禁，不用于自动搜索最优阈值，也不能把未来分钟数据、日终完整Bar或事后新闻修订注入当时决策。

## 输入契约

- 固定DataVersion、UniverseVersion、FactorSetVersion、ModelVersion和StrategyVersion。
- 当日发布且当时为ACTIVE的DailyStrategySnapshot或EnsembleStrategySnapshot。
- 带eventTime、receivedAt、availableAt和质量状态的1/5分钟Bar及MarketAnomalyEvent。
- 当时可见的MarketRegimeSnapshot、FinancialNewsEvent和PortfolioSnapshot。
- 版本化RiskPolicy、费用、滑点、最低费用、涨跌停、停牌、最小交易单位和T+1规则。
- 固定Workflow、Agent、Prompt、调仓政策、MonitorPolicy（10分钟批量采样，P0/P1/P2按10/20/30分钟评估）、阈值集和随机种子；模型输出优先使用已保存的结构化Artifact，避免回放时模型漂移改变历史。

## 对照场景

至少同时运行：

1. `DAILY_FIXED_WINDOW`：纯日频目标，在固定窗口执行，不使用盘中异常改变批次。
2. `DAILY_WITH_DELAY`：盘中规则只能延迟或取消尚未接受的第一批。
3. `DAILY_WITH_RISK_REDUCTION`：第一批后最多允许一次INTRADAY_RISK_REDUCTION。
4. `DAILY_MAX_TWO_BATCHES`：执行完整ADR-010政策，第二批还可用于EXECUTION_CORRECTION。
5. `NO_REBALANCE`：保持原组合，作为正式基准。

禁止把`0.7 × DailyAlpha + 0.3 × IntradaySignal`之类未校准分数直接加入生产对照。若未来引入盘中新Alpha，必须作为独立CANDIDATE策略重新训练、Walk-forward和Shadow。

## 回放流程

```text
历史DataVersion
  -> 当时可用DailyStrategySnapshot
  -> 逐窗口推进分钟事件时间
  -> 生产同版本MonitorPolicy / MonitorRule / Regime定义
  -> 决策门控与保存的结构化Agent结果
  -> 组合级TradeProposal和RiskEvaluation
  -> DecisionBudgetReservation / RebalanceBatch
  -> A股成交、费用、滑点和部分成交模拟
  -> PortfolioSnapshot / Outcome / Attribution
```

每一步必须保存输入Hash、availableAt、MonitorPolicy/阈值/策略/规则版本、reservationId、rebalanceBatchId和结果。回放时钟只能向前推进；迟到数据按生产迟到策略处理，不能回填并改变已完成决策。

## 指标与门禁

至少比较：

- 成本后年化收益、超额收益、Sharpe、最大回撤和尾部损失。
- 换手率、调仓批次数、OrderIntent数、部分成交率和未成交率。
- 延迟执行的价格优势/劣势、滑点、费用和容量。
- 异常触发数、进入决策数、最终HOLD数、第二批使用原因和假阳性。
- T+1、涨跌停、停牌、陈旧数据和预算拒绝次数。
- 与纯日频和NO_REBALANCE相比的增量收益、风险变化及置信区间。

硬门禁：PIT、T+1、数据新鲜度、批次上限、成本、组合风险或幂等任一失败均判定FAIL。第二批政策只有在多个样本外窗口中显示可解释的成本后改善且没有显著放大尾部风险时，才能进入阶段12 Shadow；否则保持观察、延迟执行或仅允许紧急风险减仓。

## 测试

- 相同输入、版本和随机种子重复运行结果一致。
- 任一未来分钟Bar、日终信息或迟到修订提前可见时测试失败。
- 同一RebalanceBatch的多Leg、部分成交和重报只计一次；第三批被拒绝。
- 当天新买入A股不能在第二批卖出；已有可卖持仓按可用数量处理。
- Monitor、Regime、Governance、Risk和Execution使用与生产相同的规则实现或版本化适配器。
- P0/P1/P2分别只在10/20/30分钟到期时评估，P1/P2复用同一批量快照；普通阈值不得重新计算日频Alpha或新增盘中Alpha批次。
- 任一依赖缺失时输出明确不可比较，不以默认值生成伪收益。

## 完成条件

- 五个场景都生成可复现Manifest、交易流水、组合曲线、指标和差异归因。
- 评审记录明确选择进入阶段12的批次政策、保留风险、回滚方案和签署人。
- 回放结果不自动修改ACTIVE策略、RiskPolicy、Prompt或调仓预算。
