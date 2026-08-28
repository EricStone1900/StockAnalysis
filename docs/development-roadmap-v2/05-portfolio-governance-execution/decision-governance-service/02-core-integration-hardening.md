# Governance 05-02 复核、风控、审批与强化

## 实施步骤

1. 实现RiskReviewResult不可变关联，校验decisionId、proposalVersion、packetHash和validUntil。
2. PASS_WITH_CONDITIONS只进入REVISION_REQUIRED；REJECT关闭版本；证据不足进入REVIEW_BLOCKED。
3. 调用portfolio-risk生成RiskEvaluation；只有当前版本双重PASS才能等待人工审批。
4. 实现approve、reject、modify、request-refresh和过期；修改后重新复核及硬风控。
5. 实现maxDailyTradeBatches、maxRiskReviewRevisions、全局暂停和只观察模式。
6. 发布状态事件；迟到旧版本结果只审计，不推动状态机。

## 测试

- PASS不能直接创建OrderIntent。
- 第三次交易批次被拒绝。
- 旧复核、旧风控、持仓变化和策略版本变化使结果失效。
- 连续修改超过上限进入REVIEW_BLOCKED。
- 重复审批无重复副作用。

