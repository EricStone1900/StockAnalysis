# implementation-checklist

## 1. 用途

本清单用于把架构文档转换为可执行开发计划。每个阶段只有满足验收门槛后才能进入下一阶段，避免在数据、契约和风控尚不稳定时提前实现自动交易。

逐阶段的人工执行步骤、关键代码骨架、测试案例和完成检查以[开发路线V2](../../development-roadmap-v2/README.md)为准。旧版[分阶段开发指南](../../development-phases/README.md)仅保留为领域实现示例；本文件继续保留跨阶段总门禁和发布检查。

## 2. 开工前必须决定的ADR

- ADR-001：主行情和备用行情供应商。
- ADR-002：证券主键、交易所代码和复权口径。
- ADR-003：Point-in-Time财务数据语义。
- ADR-004：PostgreSQL、Parquet、MinIO的数据归属。
- ADR-005：Qlib数据转换和版本发布方式。
- ADR-006：因子准入阈值和人工审批角色。
- ADR-007：vn.py Gateway或轮询行情接入方式。
- ADR-008：市场状态维度、状态枚举、迟滞和更新时间。
- ADR-009：DeepSeek、Claude和备用模型绑定。
- ADR-010：交易批次定义及每日上限。
- ADR-011：人工成交回填和持仓事实来源。
- ADR-012：新闻来源许可和原文保存策略。
- ADR-013：未来券商、模拟盘和生产账户隔离方案。
- ADR-014：风险复核分级、跨模型触发条件、结论合并和失败关闭策略。
- ADR-015：NATS JetStream的Stream、保留、DLQ和灾难恢复策略。
- ADR-016：限界上下文、数据库所有权和允许的同步/异步调用矩阵。
- ADR-017：Agent同镜像六部署的权限、Task Queue和模型Profile隔离。
- ADR-018：日频Strategy Plugin SDK版本、第三方Runner隔离、许可证/供应链门禁和StrategyVersion激活角色。

ADR必须记录背景、选择、备选方案、后果和生效日期。

## 3. 工程基础

- 建立pnpm workspace和Python项目边界。
- 建立packages/contracts、OpenAPI、AsyncAPI和JSON Schema生成流程。
- 统一代码格式、Lint、单元测试和Commit检查。
- 建立Docker Compose开发环境。
- 建立按服务Database/User隔离的PostgreSQL、Temporal PostgreSQL、NATS JetStream、Redis、MinIO。
- 为写服务建立Outbox Relay，为消费者建立Inbox幂等模板和DLQ操作手册。
- 每个微服务项目具备独立Dockerfile、迁移、健康检查和单独Compose启动验证。
- 建立Secrets注入方式，禁止提交.env密钥。
- 建立OpenTelemetry、日志、Metrics和correlationId。
- 所有服务实现live、ready、metrics和version端点。

验收：本地一条命令启动基础设施和空服务，各服务可独立构建/停止，所有Readiness正常，OpenAPI Client和AsyncAPI类型可生成，重复事件测试幂等。

## 4. 阶段一：市场数据

- 实现Security Master。
- 实现交易日历和交易时段。
- 实现日线行情和财务数据Adapter。
- 保存原始数据和标准数据。
- 实现DataVersion和Point-in-Time快照。
- 实现数据质量规则。
- 实现公司行动和复权。
- 为Qlib生成确定版本的数据副本。

验收：指定任意历史日期可以重建当时可见的数据；数据质量FAIL阻止发布。

## 5. 阶段二：量化研究

- 建立Qlib Adapter。
- 实现股票池历史快照。
- 实现Factor Registry和基础因子。
- 实现IC、RankIC、分层收益和成本后回测。
- 实现Model Registry和推理。
- 实现DailyAnalysisSnapshot原子发布。
- 实现Strategy Registry、Plugin SDK v1、RebalancePolicy和DailyStrategySnapshot。
- 实现NO_TRADE、低换手Top-K、多因子质量和Regime Overlay基线策略。
- 第三方策略使用隔离Runner、Manifest、SBOM、许可证和安全门禁。
- 实现当前持仓股票分析。
- 建立回测可复现记录。

验收：每天生成不可变分析与策略快照，失败时保留上一份并返回isStale=true；新插件不修改Agent/Workflow；日频计算不强制交易。

## 6. 阶段三：research-automation-service研究通道

- 建立无生产密钥的隔离执行容器。
- 实现候选因子生成和实验Artifact。
- 实现未来数据、样本外和相关性检查。
- 只生成PromotionRequest；由quant-research-service独立复验和执行CANDIDATE到ACTIVE批准流程。
- 实现因子版本回滚和废弃。

验收：RD-Agent产物不能连接生产Registry数据库，也不能绕过独立复验和准入流程影响每日生产快照。

## 7. 阶段四：Portfolio Risk、Platform API与Web

- 独立部署portfolio-risk-service和platform-api-service，分别使用独立Database/User。
- 实现人工PortfolioSnapshot、流水骨架、组合估值和RiskPolicy只读模型。
- platform-api只通过生成Client调用领域服务，不保存持仓、建议和订单事实。
- 实现认证、RBAC、幂等、入口审计、聚合查询和部分失败响应。
- React Dashboard展示量化快照、持仓、数据新鲜度和服务健康。

验收：两个服务可独立构建和迁移；跨库写权限被拒绝；BFF依赖故障不会导致整个Dashboard崩溃。

## 8. 阶段五：新闻情报

- 实现官方公告和至少两个财经来源Adapter。
- 实现原文存档和许可元数据。
- 实现URL、Hash和近似去重。
- 实现Security Master实体关联。
- 实现NewsEventCandidate。
- 接入financial-news-agent并回写FinancialNewsEvent。
- 实现来源故障和新鲜度状态。

验收：同一转载事件只分析一次，结果能追溯全部来源。

## 9. 阶段六：盯盘服务

- 选择vn.py Gateway或轮询Adapter。
- 实现MarketDataEvent和5分钟Bar。
- 实现watchlist分层和版本。
- 实现确定性异常规则。
- 实现去重、冷却、Outbox和严重度。
- 实现交易时段、午间休市、停牌和数据中断。
- 建立历史分钟数据回放。
- 积累数据后再引入River影子评分。
- 通过评估后让River参与综合分级。

验收：无异常不调用模型；重复事件不重复触发；行情断开会告警且不产生伪正常结果。

## 10. 阶段七：市场状态

- 实现TrendCalculator、BreadthCalculator、VolatilityCalculator和LiquidityCalculator。
- 实现行业相对强弱和行业状态。
- 实现RISK_ON、NEUTRAL、RISK_OFF、STRESS状态规则。
- 实现进入/退出迟滞、最短持续窗口和极端事件快速降级。
- 实现MarketRegimeSnapshot原子发布。
- 使用ruptures研究历史变化点。
- 使用Qlib回测不同状态下因子和组合表现。
- River先以影子模式运行，积累误报和漂移数据。
- 状态定义和模型经过回放、批准后才可ACTIVE。

验收：市场状态不由LLM直接计算；数据FAIL不发布新状态；状态转换可追溯输入和定义版本。

## 11. 阶段八：Agent服务、工作流和治理

- 实现Agent Registry、Runner、Tool Registry和Prompt Registry。
- 用同一agent-service镜像配置六个独立部署、Task Queue、Durable Consumer和Tool权限。
- 实现DeepSeek Provider和通用OpenAI兼容Provider。
- 实现Anthropic Provider。
- 实现模型能力矩阵和逻辑Profile。
- 实现Zod输出校验、工具白名单和审计。
- 实现股票、新闻、市场、盯盘、主决策和风险Agent。
- 股票分析Agent和主决策Agent只读取`ACTIVE` DailyStrategySnapshot，不运行插件、不激活版本、不修改策略参数或组合权重。
- ContextBuilder校验StrategyVersion状态、DataVersion、股票池、成本模型、新鲜度和代码/镜像Digest，并把策略分歧显式写入证据包。
- 风险复核确定性检查换手、成本、滑点、容量、市场状态适配和NO_TRADE基线，LLM只负责独立质疑和结构化解释。
- market-state-agent只解释MarketRegimeSnapshot，不直接读取全市场原始行情。
- 实现RiskReviewEvidencePacket校验、独立证据判断、建议对照、反方情景和结构化RiskReviewResult。
- 实现PASS、PASS_WITH_CONDITIONS、REJECT和INSUFFICIENT_EVIDENCE四种结果。
- 实现高风险建议的DeepSeek主决策与Claude独立复核，以及备用Provider和确定性分歧合并。
- 参考TradingAgents的多空与风险视角建立测试用例，但不把研究框架接入生产硬风控。
- 建立Golden Dataset和跨模型契约测试。

验收：替换模型不修改业务Agent；新增合规策略插件不修改Agent/Workflow；任何建议都可追溯输入、StrategyVersion、插件Digest和模型运行；证据不足、模型冲突、非ACTIVE策略或所有Provider失败不会默认放行。

### Workflow和治理

- 实现每日量化、新闻、盯盘、决策和审批Workflow。
- 实现日频和盘中MarketRegimeWorkflow。
- 实现Activity幂等和错误分类。
- 实现决策触发门控和冷却。
- 实现TradeProposal状态机。
- 实现proposalVersion与RiskReviewResult不可变关联，以及REVISION_REQUIRED和REVIEW_BLOCKED分支。
- 实现maxRiskReviewRevisions并验证修订循环达到上限后转人工处理。
- 实现RiskEvaluation。
- 实现人工批准、拒绝、修改和过期。
- 实现每日最多1～2个交易批次。
- 实现全局暂停和只观察模式。

验收：Worker重启不丢状态；修改建议一定重新风控；重复审批不创建重复指令。

## 12. 阶段九：人工执行

- 实现OrderIntent。
- 实现人工提交、成交、撤销回填。
- 实现成交幂等和持仓流水。
- 实现日终人工对账。
- 实现决策到成交的完整时间线。

验收：只有已批准且风控有效的建议能创建READY指令；重复成交回填不重复入账。

## 13. 阶段十：模拟盘和自动交易

进入条件：

- 数据和快照稳定运行足够周期。
- 异常检测假阳性和漏报经过回放评估。
- 决策和风控审计完整。
- 人工模式对账无未解决差异。
- Kill Switch完成独立测试。

实施顺序：

    Paper Trading
      -> Shadow Trading
      -> 小资金白名单自动交易
      -> 多账户受控扩展

禁止从人工模式直接跳到完整自动交易。

## 14. 测试矩阵

每个服务至少具备：

- 单元测试。
- API Contract Test。
- Consumer Contract Test。
- 数据Schema兼容测试。
- 幂等和重复消息测试。
- 超时、限流和依赖故障测试。
- 历史回放测试。
- 时区、交易日和边界日期测试。
- 数据过期和缺失测试。
- 权限和密钥泄漏测试。

关键端到端场景：

1. 每日量化成功并发布快照。
2. 每日量化失败并安全使用旧快照。
3. 重大新闻触发重新决策。
4. 盘中异常触发盯盘Agent但最终HOLD。
5. 市场状态从NEUTRAL变为RISK_OFF并触发重评估。
6. 市场状态数据FAIL时继续使用旧快照并标记过期。
7. 风险规则拒绝Agent买入建议。
8. 人工修改建议后重新执行风险复核和确定性硬风控。
9. 重复审批和重复成交保持幂等。
10. 行情断开、恢复和数据补发。
11. 模型超时后受控降级。
12. 券商状态UNKNOWN时禁止重复下单。
13. 风险复核PASS后仍被确定性硬风控拒绝。
14. PASS_WITH_CONDITIONS生成新proposalVersion并重新复核。
15. 证据缺失、过期或跨模型冲突时进入REVIEW_BLOCKED或人工关注状态。
16. 迟到的旧proposalVersion复核结果不能推动当前决策状态。
17. 风险复核连续要求修改达到maxRiskReviewRevisions后停止自动循环。
18. 新增第三方日频策略通过Manifest和隔离Runner接入，无需修改Agent或Workflow代码。
19. 第三方策略尝试访问数据库、网络、文件系统越界或生产密钥时被隔离并审计。
20. `CANDIDATE`策略不能进入Agent上下文，StrategyVersion或成本模型变化使旧EvidencePacket失效。
21. 所有日频策略均可输出NO_REBALANCE；每日计算成功不增加交易批次。

## 15. 每次发布检查

- 数据库迁移向前兼容并有回滚策略。
- OpenAPI和事件Schema无未声明破坏性变更。
- 新Prompt、模型、因子和风险规则均有发布版本。
- Dashboard可以显示数据新鲜度和服务健康。
- 告警规则和Runbook已更新。
- 备份、恢复和对象存储留存策略已经验证。
- 新服务已定义可接受延迟、数据新鲜度和错误率告警阈值。
- 没有跨服务直接写数据库。
- 没有在日志中记录密钥、完整Prompt私密数据或券商凭据。
- 功能开关默认保持人工模式和自动交易关闭。
