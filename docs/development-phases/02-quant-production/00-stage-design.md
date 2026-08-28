# 阶段02：量化与日频策略生产闭环总设计

## 目标

在独立`services/quant-research-service`中，基于阶段01的数据实现Qlib生产分析、因子、模型、可扩展日频策略、可复现回测及每日不可变快照。

## 开发边界

生产通道只使用ACTIVE因子、模型和策略；输出信号、排名、候选目标组合和证据，不输出最终Order或批准结果。

## 实施要求

- 每次任务显式绑定数据、股票池、因子集和模型版本。
- 候选股与持仓股必须同时分析。
- 评价必须包含样本外和交易成本。
- 部分结果不能发布为正式快照。
- 使用独立Database/User，通过Outbox发布`DailyAnalysisPublished`事件；不安装或运行RD-Agent。
- 日频表示每天评估，不强制每天调仓；再平衡由版本化RebalancePolicy控制。
- 第三方策略通过Plugin SDK接入，默认在隔离Runner容器运行。

## 顺序文档

1. [Qlib数据集、股票池和Factor Registry](./01-qlib-dataset-factor-registry.md)
2. [因子评价、模型和回测](./02-evaluation-model-backtest.md)
3. [每日分析快照与API](./03-daily-analysis-snapshot.md)
4. [可扩展日频策略、插件SDK和第三方接入](./04-daily-strategy-platform.md)

## 阶段验收

- 每日生成候选股和持仓股分析。
- 快照发布原子化，失败安全沿用旧版本并标记过期。
- 因子和模型有稳定版本与状态。
- 回测可以由数据、代码和配置版本复现。
- 新增兼容策略插件不修改Agent和Workflow代码。
- 第三方策略不能访问生产数据库、模型和交易权限。
- 日频策略可以连续返回NO_REBALANCE。
