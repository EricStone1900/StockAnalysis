# 阶段11 Ubuntu 人工验收步骤

本步骤验证交易结果评估、Decision Memory、策略学习草稿和候选晋升闭环。学习输出只能进入研究和人工审批流程，不能在线修改 ACTIVE 策略。

## 1. 固定版本与本机检查

```sh
git clone https://github.com/EricStone1900/StockAnalysis.git
cd StockAnalysis
git checkout <待验收CommitSHA>
corepack enable
pnpm install --frozen-lockfile
cd services/quant-research-service
UV_CACHE_DIR="$PWD/../../.uv-cache" uv run ruff check .
UV_CACHE_DIR="$PWD/../../.uv-cache" uv run mypy src
UV_CACHE_DIR="$PWD/../../.uv-cache" uv run pytest tests/unit/test_outcome_evaluator.py -o addopts=''
cd ../agent-service
pnpm lint
pnpm typecheck
pnpm test
cd ../..
```

记录 Commit SHA、数据版本、StrategyVersion、PromptVersion、实验版本和工具版本。

## 2. Outcome Evaluator 验收

准备包含周末/节假日的交易日历、决策日、成交价格、基准价格、费用和滑点。确认 5/20/60 交易日窗口只按交易日推进，窗口未关闭时拒绝评估；验证 `FILLED`、`REJECTED`、`HOLD`、`EXPIRED`、`SHADOW` 分开保存，不混合收益口径。

重复相同决策和 ProposalVersion，确认只产生一个相同版本；提交晚到更正时确认追加新版本、旧 Outcome 保留且 Content Hash 可追溯。

## 3. Decision Memory 投影与检索

投影真实成交、人工拒绝、HOLD 和 Shadow 样本，查询时验证跨 Portfolio、未来 `availableAt`、失效状态、污染内容和 Hash 错误均被排除。设置成功与反例配额，确认两类样本均能召回；删除投影后从事件/API 重建，确认 Content Hash 与原结果一致。

## 4. 策略学习 Agent 验收

提供已关闭 Outcome、Memory、人工反馈、反例和当前 ACTIVE StrategyVersion。确认单次盈利/亏损、小样本、无反例、样本类型不足或未来 Outcome 均不能生成学习草稿；合格输入只生成 `DRAFT`，包含支持样本、反例、样本分布和待验证实验，且无激活、Prompt 发布、RiskPolicy 或 Order 权限。

## 5. 候选实验与晋升验收

按顺序执行 `SELECTED → VALIDATED → SHADOW → APPROVED → ACTIVE`。逐项让 PIT、样本外、Walk-forward、成本、换手、容量、Regime 或相关性验证失败，确认候选进入 `REJECTED`。没有人工批准编号不得进入 `APPROVED`；批准编号不匹配不得激活。激活后模拟漂移，确认可审计地 `SUSPENDED`，不在线调参。

## 6. 研究隔离与回滚

确认候选实验使用独立 Artifact、数据版本和实验家族记录，不能写入生产 Strategy Registry 的 ACTIVE 状态。保留 Outcome、Memory、Draft、Experiment、Validation、Shadow、Approval 的 Hash 和审计链；失败时回滚到上一 ACTIVE StrategyVersion，不删除历史事实。

## 7. 判定标准

未来数据泄漏、样本混用、Hash 不一致、证据缺失、自动激活、权限越界或回滚失败均判定 FAIL。通过后记录测试报告、风险、回滚版本、数据/策略/实验版本和验收人。
