# 股票分析智能体系统分阶段开发指南

> 本目录自2026-08-28起作为领域实现示例保留，不再作为开发顺序和阶段门禁。新的实施顺序、独立微服务生命周期、专项测试和验收以[开发路线V2](../development-roadmap-v2/README.md)为准。

## 1. 使用方式

本目录把[整体设计基线](../architecture/stock-analysis-agent-system-design.md)转换为可以人工逐步执行的开发任务。

执行规则：

1. 严格按阶段编号推进，除非阶段总设计明确允许并行。
2. 进入阶段前先完整阅读该阶段的`00-stage-design.md`。
3. 按子文档编号顺序实现，不跳过测试和完成条件。
4. 每完成一份子文档，在对应“完成检查”中记录代码提交、测试命令和结果。
5. 阶段验收未通过，不进入下一阶段。
6. 文档中的代码是关键骨架，实际实现必须补齐错误处理、类型、日志和测试。
7. 架构边界变化先写ADR，再修改整体设计、服务设计和阶段文档。
8. 每个阶段新增的基础能力都必须落在独立微服务项目中，完成独立镜像、Database/User、契约和单独启动验证。
9. 领域事实通过NATS JetStream + Outbox/Inbox传播，长流程由Temporal编排，需要即时确认的命令使用REST/OpenAPI。

## 2. 阶段索引

| 阶段 | 目标 | 主要产物 | 入口 |
|---|---|---|---|
| 00 | 工程、基础设施、契约和CI基础 | 独立服务骨架、Docker、NATS/Temporal、OpenAPI/AsyncAPI、统一观测 | [阶段设计](./00-foundation-contracts/00-stage-design.md) |
| 01 | 市场数据事实基础 | Security、Calendar、PIT、DataVersion | [阶段设计](./01-market-data/00-stage-design.md) |
| 02 | Qlib量化与日频策略生产闭环 | 因子、模型、策略插件、回测、DailyAnalysisSnapshot和DailyStrategySnapshot | [阶段设计](./02-quant-production/00-stage-design.md) |
| 03 | RD-Agent隔离研究 | 独立research-automation-service、候选Artifact和Promotion Request | [阶段设计](./03-rd-agent-research/00-stage-design.md) |
| 04 | Portfolio Risk、Platform API与前端 | 独立持仓风控服务、BFF、研究Dashboard | [阶段设计](./04-platform-core-web/00-stage-design.md) |
| 05 | 新闻情报基础闭环 | 采集、去重、实体关联和Agent分析契约；真实Agent在阶段08接入 | [阶段设计](./05-news-intelligence/00-stage-design.md) |
| 06 | 交易时段盯盘 | Bar、异常规则、River、事件和回放 | [阶段设计](./06-market-monitor/00-stage-design.md) |
| 07 | 市场和行业状态 | Regime特征、状态机、快照和解释 | [阶段设计](./07-market-regime/00-stage-design.md) |
| 08 | Agent、Temporal和决策治理 | 通用Agent镜像的六个部署、Workflow、独立治理服务和人工审批 | [阶段设计](./08-agent-workflow-governance/00-stage-design.md) |
| 09 | 人工执行和端到端闭环 | OrderIntent、成交、流水、对账 | [阶段设计](./09-manual-execution/00-stage-design.md) |
| 10 | 模拟盘和受控自动交易 | Paper、Shadow、Kill Switch、容量与基础设施扩缩容 | [阶段设计](./10-paper-shadow-auto/00-stage-design.md) |

## 3. 统一完成记录

阶段进度建议直接维护为：

- [ ] 阶段00：工程与契约基础
- [ ] 阶段01：市场数据
- [ ] 阶段02：量化生产闭环
- [ ] 阶段03：RD-Agent研究通道
- [ ] 阶段04：Portfolio Risk、Platform API与Web
- [ ] 阶段05：新闻情报
- [ ] 阶段06：盘中市场监控
- [ ] 阶段07：市场状态
- [ ] 阶段08：Agent、工作流和治理
- [ ] 阶段09：人工执行
- [ ] 阶段10：模拟盘和受控自动交易

每份子文档完成后建议在PR或开发日志中记录：

```text
阶段/文档：
代码提交：
实现范围：
未实现范围：
执行测试：
测试结果：
产生的Schema/API变更：
产生的ADR：
已知风险：
下一步：
```

## 4. 全局禁止事项

- 不允许Agent直接写持仓、风险策略或订单。
- 不允许跨微服务直接写其他领域Database或Schema。
- 不允许用当前时间替代历史`availableAt`进行回测。
- 不允许RD-Agent候选代码自动进入生产。
- 不允许用旧快照、旧复核或旧风控结果静默放行。
- 不允许在日志、Fixture或文档中保存真实密钥。
- 不允许从人工执行阶段直接跳到完整自动交易。
- 不允许用事件总线替代必须返回确定结果的硬风控、审批和OrderIntent命令。
