# 10-03 人工审批、成交与完整E2E

## 实施步骤

1. Web展示Evidence Bundle、Proposal、RiskReview、RiskEvaluation和版本。
2. Approver可以批准、拒绝、修改或请求刷新；所有操作要求原因和幂等键。
3. 修改产生新ProposalVersion并重新走风险复核和硬风控。
4. 批准后调用trade-execution创建READY Intent；ExecutionOperator人工下单并回填Fill。
5. Fill更新portfolio Ledger/Snapshot，并完成决策到结果的审计时间线。
6. 日终运行对账，未解决差异阻止进一步自动化。

```text
Data -> Quant/Strategies -> Specialists -> Main Proposal
  -> Risk Review -> Hard Risk -> Human Approval
  -> Manual OrderIntent/Fill -> Portfolio -> Reconciliation
```

## 测试

- 正常BUY、正常SELL、HOLD、人工拒绝和人工修改。
- 第3批、过期、持仓变化和价格偏差拒绝。
- 重复按钮、重复Fill和浏览器重试保持幂等。

