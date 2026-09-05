# 阶段11验收

- [ ] DecisionOutcome确定性计算和多窗口通过。
- [ ] 真实、拒绝、HOLD和Shadow样本口径隔离。
- [ ] Decision Memory可重建且无未来泄漏。
- [ ] Strategy Learning Agent只生成草稿和实验请求。
- [ ] 支持样本与反例同时进入经验评估。
- [ ] RD-Agent候选经过quant独立复算和Shadow。
- [ ] 生产Strategy/Memory版本仍需人工批准。
- [ ] 漂移、SUSPEND和回滚路径通过。
- [ ] 学习服务故障不影响生产决策链。

## 当前实现证据

- Outcome Evaluator 提交：`059d1df`；Decision Memory 提交：`9c11f56`。
- strategy-learning-agent 提交：`c45afbe`；候选验证与晋升状态机提交：`3ede923`。
- Mac 验证已通过 Python Ruff、mypy、Outcome 测试，以及 Agent 服务 ESLint、TypeScript 和 43 项单元测试。
- 已覆盖确定性数值计算、未来数据隔离、成功/反例配额、最小样本、独立验证、Shadow、人工批准、激活和暂停。
- 阶段11尚未最终验收，必须完成 `05-ubuntu-e2e-verification.md` 并记录数据版本、策略版本、实验版本、Artifact Hash 和签署人。
