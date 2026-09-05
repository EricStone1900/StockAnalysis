# 阶段09验收

- [ ] 四个专业Agent分别通过Fake和真实只读Tool契约。
- [ ] 主决策Agent可输出可追溯组合级HOLD/REBALANCE草稿及多个BUY/SELL Leg。
- [ ] 同一目标组合不能拆成多个单票Proposal规避批次或组合风险。
- [ ] 风险复核独立模型、证据包和四类结论通过。
- [ ] Golden Dataset和跨模型回归门禁生效。
- [ ] 过期、冲突、证据不足和Provider失败不会放行。
- [ ] Agent不能运行插件、写领域事实、改RiskPolicy或下单。
- [ ] 六个Agent可独立部署、授权和扩缩容。

## 当前实现证据

- 专业 Agent 提交：`922dd79`（股票分析）、`0aaf594`（财经新闻）、`1af3b2d`（盯盘）、`e27cc05`（市场状态）。
- 主决策 Agent 提交：`793bc86`；风险复核 Agent 提交：`a0011bc`；Golden 评估提交：`0cdd1d5`。
- Mac 本地验证已通过 ESLint、TypeScript 和 34 项单元测试；Golden Fixture 共 60 项。
- 已覆盖输入快照边界、证据引用、策略冲突、NO_REBALANCE、组合级 Proposal、RiskReviewEvidencePacket Hash、四类风险结论和跨模型保守合并。
- 阶段09尚未最终验收，必须完成 `05-ubuntu-e2e-verification.md` 的人工检查并记录提交、镜像、配置、日志和签署人。
