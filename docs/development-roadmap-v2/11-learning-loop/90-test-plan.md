# 阶段11测试计划

- Outcome：5/20/60交易日、基准、MFE/MAE、成本、滑点和更正版本。
- 时间：所有Context只含`availableAt <= decisionAsOf`，历史回放无未来Outcome。
- Memory：Scope、状态、反例、多样性、Hash、重建和降级。
- Learning Agent：小样本、单次盈亏、确认偏差、样本类型混用和恶意Memory。
- Research Loop：Sandbox、独立复算、Champion/Challenger、Shadow和人工批准。
- 权限：学习Agent/RD-Agent不能激活策略、改Prompt、RiskPolicy或Order。
- Idempotency：重复Outcome、重复Draft和重复Promotion不产生重复版本。

必须使用时间冻结的历史决策点T完成一次端到端回放。

## 当前本机验证记录（Mac）

- Outcome Evaluator 已覆盖交易日窗口、未来数据拒绝、幂等版本、更正追加和 EpisodeType 隔离。
- Decision Memory 已覆盖 Portfolio 范围、availableAt、状态、Hash、删除重建和成功/反例配额。
- strategy-learning-agent 已覆盖最小样本、反例、EpisodeType 多样性、未来 Outcome 拒绝和 DRAFT 输出。
- 候选策略晋升状态机已覆盖 PIT、样本外、Walk-forward、成本、换手、容量、Regime、相关性和人工批准门禁。
- Python Ruff、mypy、Outcome 单元测试及 Agent 服务 ESLint、TypeScript、43 项单元测试已通过。
- 尚待 Ubuntu 人工验收：真实 Outcome 输入、Memory 重建、研究实验隔离、Shadow 和人工晋升审计。
