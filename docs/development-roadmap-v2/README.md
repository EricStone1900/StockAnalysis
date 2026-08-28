# 股票分析智能体系统开发路线 V2

- 版本：2.0
- 基线日期：2026-08-28
- 状态：已批准执行
- 目标：先完成可独立部署的领域微服务，再建设Agent、工作流、学习闭环和自动交易

## 1. 使用规则

1. 严格按00～12阶段推进；只有阶段总设计明确标记可并行的工作才允许并行。
2. 每阶段先读`00-stage-design.md`，按编号执行实现文档，最后执行`90-test-plan.md`和`99-acceptance.md`。
3. 每个微服务必须按[微服务生命周期](./standards/microservice-lifecycle.md)从骨架、最小纵向切片逐步发展到生产强化。
4. 测试证据和签署规则以[测试与验收标准](./standards/test-and-acceptance-standard.md)为准。
5. 上游未完成时使用什么Fake、何时切换真实依赖，以[开发依赖矩阵](./00-architecture-baseline/03-development-dependency-matrix.md)为准。
6. 阶段验收未签署，不进入下一阶段；临时跳过项必须写ADR并标记阻塞影响。
7. 旧版[开发指南](../development-phases/README.md)保留为领域代码示例来源；开发顺序和阶段门禁以本文为准。

## 2. 总体阶段

| 阶段 | 目标 | 入口 |
|---|---|---|
| 00 | 架构基线、服务边界、依赖和测试规则冻结 | [阶段设计](./00-architecture-baseline/00-stage-design.md) |
| 01 | 工程框架、基础设施、契约工具链和所有服务空骨架 | [阶段设计](./01-engineering-foundation/00-stage-design.md) |
| 02 | 独立完成market-data-service | [阶段设计](./02-market-data-service/00-stage-design.md) |
| 03 | 独立完成quant-research-service及日频策略平台 | [阶段设计](./03-quant-research-service/00-stage-design.md) |
| 04 | 独立完成research-automation-service | [阶段设计](./04-research-automation-service/00-stage-design.md) |
| 05 | 独立完成Portfolio Risk、Decision Governance和人工Execution基础 | [阶段设计](./05-portfolio-governance-execution/00-stage-design.md) |
| 06 | 独立完成新闻、盯盘和市场状态服务 | [阶段设计](./06-market-intelligence/00-stage-design.md) |
| 07 | Platform API和React Web访问层 | [阶段设计](./07-platform-access/00-stage-design.md) |
| 08 | Agent Kernel、多模型网关、Tool/Prompt和Memory M0 | [阶段设计](./08-agent-foundation/00-stage-design.md) |
| 09 | 四个专业Agent、主决策Agent和风险复核Agent | [阶段设计](./09-business-agents/00-stage-design.md) |
| 10 | Temporal工作流、人工审批、成交回填和完整E2E | [阶段设计](./10-workflow-manual-e2e/00-stage-design.md) |
| 11 | Outcome、Decision Memory、策略学习和受治理晋升闭环 | [阶段设计](./11-learning-loop/00-stage-design.md) |
| 12 | Paper、Shadow、券商适配和受控自动交易 | [阶段设计](./12-paper-shadow-auto/00-stage-design.md) |

## 3. 总门禁

```text
Architecture Gate
  -> Engineering Gate
  -> Independent Service Gates
  -> Platform Gate
  -> Agent Foundation Gate
  -> Agent Application Gate
  -> Manual E2E Gate
  -> Learning Safety Gate
  -> Paper/Shadow Gate
  -> Controlled Automation
```

- 阶段01以前不写领域业务。
- 单个微服务没有独立通过验收，不允许成为Agent Tool或Temporal Activity的真实依赖。
- 阶段08以前一律使用Fake Agent；阶段10以前不形成真实交易闭环。
- 阶段11只能自动生成事实结果、经验草稿和策略候选，不能自动激活生产策略。
- 阶段12以前自动交易Feature Flag始终关闭。

## 4. 进度

- [ ] 00 架构基线
- [ ] 01 工程基础
- [ ] 02 市场数据
- [ ] 03 量化生产
- [ ] 04 自动研究
- [ ] 05 组合、治理、执行基础
- [ ] 06 市场情报
- [ ] 07 平台访问层
- [ ] 08 Agent基础
- [ ] 09 业务Agent
- [ ] 10 人工E2E
- [ ] 11 学习闭环
- [ ] 12 Paper、Shadow和自动化
