# 10-03 人工审批、成交与完整E2E

## 实施步骤

1. Web展示Evidence Bundle、Proposal、RiskReview、RiskEvaluation和版本。
2. Approver可以批准、拒绝、修改或请求刷新；所有操作要求原因和幂等键。
3. 修改产生新ProposalVersion并重新走风险复核和硬风控。
4. 批准后调用Governance原子预留DecisionBudgetReservation，再调用trade-execution原子创建一个RebalanceBatch及多个READY Intent；ExecutionOperator按Leg人工下单并回填Fill。
5. Fill更新portfolio Ledger/Snapshot，并完成决策到结果的审计时间线。
6. 日终运行对账，未解决差异阻止进一步自动化。
7. 发送执行前预留转DISPATCHING；执行服务接受批次后消费预留，明确未接受时释放。响应不确定时按稳定幂等键查询，接受成功后的部分成交、撤销、过期或失败不恢复额度。

```text
Data -> Quant/Strategies -> Specialists -> Main Proposal
  -> Risk Review -> Hard Risk -> Human Approval
  -> Budget Reservation -> RebalanceBatch -> Manual OrderIntent[]/Fill[]
  -> Portfolio -> Reconciliation
```

## 测试

- 正常多Leg REBALANCE、HOLD、人工拒绝和人工修改。
- 第3批、非法第二批reason、过期、持仓变化和价格偏差拒绝。
- 重复按钮、重复Fill和浏览器重试保持幂等。
- 任一Leg在原子接受前失败时无部分READY Intent；同批次部分成交和重报不增加批次。
