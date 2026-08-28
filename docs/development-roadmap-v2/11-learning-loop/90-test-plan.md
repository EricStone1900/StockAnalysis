# 阶段11测试计划

- Outcome：5/20/60交易日、基准、MFE/MAE、成本、滑点和更正版本。
- 时间：所有Context只含`availableAt <= decisionAsOf`，历史回放无未来Outcome。
- Memory：Scope、状态、反例、多样性、Hash、重建和降级。
- Learning Agent：小样本、单次盈亏、确认偏差、样本类型混用和恶意Memory。
- Research Loop：Sandbox、独立复算、Champion/Challenger、Shadow和人工批准。
- 权限：学习Agent/RD-Agent不能激活策略、改Prompt、RiskPolicy或Order。
- Idempotency：重复Outcome、重复Draft和重复Promotion不产生重复版本。

必须使用时间冻结的历史决策点T完成一次端到端回放。

