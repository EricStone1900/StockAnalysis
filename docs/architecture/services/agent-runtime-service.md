# agent-service（原agent-runtime-service）

## 1. 定位

通用Node.js/TypeScript Agent微服务项目。它只维护一套Agent Kernel和多模型网关，但通过同一镜像的六个独立部署运行六个业务Agent，屏蔽DeepSeek、Claude、OpenAI及其他Provider差异。

每个部署必须拥有独立`AGENT_ID`、Prompt版本、模型Profile、Tool白名单、NATS Durable Consumer、Temporal Task Queue和资源限制。共享代码不意味着同一进程或同一故障域。

推荐技术栈：TypeScript、Vercel AI SDK、Zod、OpenTelemetry。OpenAI Agents SDK 可作为可选适配器，不作为不可替换的业务核心。

## 2. Agent 组成和开源组件对应关系

最终采用“主Agent + 5个专业Agent”，合计6个业务Agent。所有Agent使用同一自研TypeScript Agent Kernel工程和镜像，以六个容器独立运行，共用以下基础组件：

- [Vercel AI SDK](https://github.com/vercel/ai)：模型调用、工具调用、流式响应和Provider适配基础；业务接口不能直接依赖厂商SDK。
- [Zod](https://github.com/colinhacks/zod)：输入输出Schema、枚举和数值范围校验。
- [Temporal TypeScript SDK](https://github.com/temporalio/sdk-typescript)：在agent-runtime-service外部编排调度、重试、超时、等待和人工审批；它不是Agent推理框架。
- [OpenTelemetry JS](https://github.com/open-telemetry/opentelemetry-js)：调用链、模型耗时、Token、错误和降级观测。
- PostgreSQL、Redis和S3/MinIO：保存业务状态、缓存、审计和模型Artifact，不使用模型厂商会话作为长期事实来源。

DeepSeek、Claude和OpenAI属于可切换模型服务，不是本系统必须绑定的开源Agent框架。DeepSeek及其他OpenAI格式模型走GenericOpenAICompatibleProvider；Claude走独立AnthropicProvider。

| Agent | 职责和主要输入 | 对应内部服务 | 主要开源框架或项目 | 推荐模型服务与采用方式 |
|---|---|---|---|---|
| stock-analysis-agent | 解释每日量化选股、因子贡献、回测摘要和当前持仓分析 | [quant-research-service](./quant-research-service.md)、[portfolio-risk-service](./portfolio-risk-service.md) | [Qlib](https://github.com/microsoft/qlib)负责因子、模型和回测；[RD-Agent](https://github.com/microsoft/RD-Agent)只负责隔离研究通道中的候选因子/模型研发 | DeepSeek推理模型为主。Agent只读取已发布DailyAnalysisSnapshot，不直接运行Qlib或接受RD-Agent候选结果进入生产 |
| financial-news-agent | 对候选股票和持仓股票的新闻事件判断方向、强度、时效和价格影响 | [news-intelligence-service](./news-intelligence-service.md) | [FinNLP](https://github.com/AI4Finance-Foundation/FinNLP)用于财经数据采集适配参考；[AKShare](https://github.com/akfamily/akshare)用于原型数据接口；[RSSHub](https://github.com/DIYgod/RSSHub)用于自建RSS入口；pgvector用于语义检索 | DeepSeek快速模型做初筛，推理模型处理重要事件。采集、去重和实体关联在Python服务完成，Agent只分析结构化NewsEventCandidate及证据 |
| market-monitor-agent | 解释交易时段HIGH/CRITICAL异常行情事件，输出IGNORE、WATCH、REASSESS或RISK_ESCALATION | [market-monitor-service](./market-monitor-worker.md)、[market-data-service](./market-data-service.md) | [vn.py](https://github.com/vnpy/vnpy)用于行情Gateway与事件接入；[River](https://github.com/online-ml/river)用于在线异常和漂移评分；确定性异常规则负责主要触发 | DeepSeek快速模型即可，只有异常事件才调用。Agent不接Tick流、不计算5分钟Bar，也不控制止损或订单 |
| market-state-agent | 解释指数、市场宽度、波动、流动性、资金和行业状态对候选股及组合的影响 | [market-regime-service](./market-regime-service.md)、[market-data-service](./market-data-service.md) | [Qlib](https://github.com/microsoft/qlib)做历史条件回测；[River](https://github.com/online-ml/river)做影子在线漂移；[ruptures](https://github.com/deepcharles/ruptures)做离线变化点研究；AKShare/vn.py提供原型或盘中数据接入 | DeepSeek推理模型为主。Agent只解释MarketRegimeSnapshot，不直接计算Regime或修改RiskPolicy |
| main-decision-agent（主Agent） | 汇总股票、新闻、盯盘、市场状态、持仓和风险证据，形成版本化BUY、SELL或HOLD建议 | 上述全部分析服务、[workflow-orchestration-service](./workflow-orchestration-service.md)、[decision-governance-service](./decision-governance-service.md) | 自研Agent Kernel + Vercel AI SDK + Zod；[TradingAgents](https://github.com/TauricResearch/TradingAgents)和[FinRobot](https://github.com/AI4Finance-Foundation/FinRobot)仅用于角色分工和流程参考 | DeepSeek推理模型为主，可配置Claude/OpenAI影子模型。Temporal负责外层流程，主Agent不能直接审批、修改硬风控或下单 |
| risk-review-agent | 独立核对建议、证据、反方观点、下行情景和投资逻辑失效条件 | [agent-runtime-service](./agent-runtime-service.md)、[decision-governance-service](./decision-governance-service.md)、[portfolio-risk-service](./portfolio-risk-service.md)只读风险快照 | TradingAgents主要参考多空和激进/中性/保守风险视角；FinRobot参考财务风险证据；[ai-hedge-fund](https://github.com/virattt/ai-hedge-fund)参考Risk Manager/Portfolio Manager分离；[LangGraph.js](https://docs.langchain.com/oss/javascript/langgraph/overview)仅作为复杂内部复核图的可选实现 | Claude作为独立复核模型，DeepSeek作为备用或第二意见。它不替代portfolio-risk-service；[Open Policy Agent](https://www.openpolicyagent.org/)未来如采用也属于确定性硬风控层 |

采用关系必须理解为：

    Python开源框架/数据Adapter
      -> 专业微服务计算并发布结构化快照或事件
      -> TypeScript Agent通过Tool Registry读取
      -> 模型解释和生成结构化判断
      -> Zod、证据校验、治理状态机和硬风控

除Vercel AI SDK、Zod等公共运行组件外，Qlib、RD-Agent、FinNLP、vn.py、River和ruptures都运行在对应Python服务或Worker中，不作为Node.js Agent进程的直接依赖。RD-Agent专属[research-automation-service](./research-automation-service.md)。TradingAgents、FinRobot和ai-hedge-fund初期只作架构、Prompt和测试场景参考，不直接接管生产决策链路。

## 2.1 部署拓扑

```text
agent-service:version
  + AGENT_ID=stock-analysis     -> stock-analysis-agent
  + AGENT_ID=financial-news     -> financial-news-agent
  + AGENT_ID=market-monitor     -> market-monitor-agent
  + AGENT_ID=market-state       -> market-state-agent
  + AGENT_ID=main-decision      -> main-decision-agent
  + AGENT_ID=risk-review        -> risk-review-agent
```

每个容器只加载一个AgentDefinition，订阅自己的NATS Subject并轮询自己的Temporal Task Queue。需要扩容时按Agent单独增加副本；主决策与风险复核不得因新闻或盯盘流量被挤占。

## 3. Agent Kernel

内部模块：

    AgentRunner
      -> AgentRegistry
      -> PromptRegistry
      -> ContextBuilder
      -> ToolRegistry
      -> ModelRouter
      -> OutputValidator
      -> GuardrailRunner
      -> AuditRecorder

Agent 定义只声明：

- instructions 和 promptVersion。
- modelProfile 和 requiredCapabilities。
- 允许调用的工具。
- Zod 输出 Schema。
- 最大工具调用次数、超时和 Token 预算。
- 输入输出 Guardrails。

## 4. 模型网关

逻辑模型 Profile：

- fast
- reasoning
- news-analysis
- risk-review
- vision
- fallback

Provider Adapter：

- DeepSeekProvider
- AnthropicProvider
- OpenAIProvider
- GenericOpenAICompatibleProvider
- LocalModelProvider

能力矩阵至少记录：

- textGeneration
- structuredOutput
- toolCalling
- parallelToolCalls
- reasoning
- vision
- streaming
- promptCaching
- serverSideConversation

业务 Agent 只依赖公共能力。厂商专有参数必须留在 Provider Adapter 中。

## 5. 工具边界

Agent 只允许通过 Tool Registry 访问：

- 最新量化快照和ACTIVE日频策略快照。
- 股票因子贡献和回测摘要。
- 结构化新闻事件和原始证据。
- 市场状态和行情异常。
- 当前持仓、资金和风险暴露。
- 确定性计算服务。

market-monitor-agent只接收 [shared-contracts](./shared-contracts.md) 定义的MarketAnomalyEvent或eventId，不接收连续Tick流。输出为IGNORE、WATCH、REASSESS或RISK_ESCALATION，并必须引用原anomalyEventId和evidenceIds。

market-state-agent只接收 [market-regime-service](./market-regime-service.md) 发布的MarketRegimeSnapshot和组合上下文，不直接读取全市场原始行情。它输出MarketRegimeAssessment，但不能修改市场状态、生产因子权重或RiskPolicy。

Agent只读取[日频策略平台](./daily-strategy-extension-design.md)发布的结构化策略快照。stock-analysis-agent解释个股策略信号，main-decision-agent比较策略共识与冲突，risk-review-agent检查NO_TRADE基准、成本、适用Regime和数据新鲜度；任何Agent都不能运行第三方策略代码或临时修改策略权重。

禁止工具：

- 未审批时直接下单。
- 修改生产因子状态。
- 修改风险上限。
- 读取生产密钥。
- 执行任意代码或任意 SQL。

## 6. 输出契约

主决策建议至少包含：

    decisionId
    asOf
    action: BUY | SELL | HOLD
    symbol
    targetWeight
    confidence
    reasons[]
    risks[]
    evidenceIds[]
    assumptions[]
    dataFreshness
    modelRunMetadata

输出先通过 Zod，再检查 evidenceId 是否存在、数据是否过期、数值是否在范围内。未通过时只能重试、降级或拒绝，不允许把原始文本直接送入交易治理层。

## 7. 模型路由建议

初始可配置为：

- 新闻初筛：DeepSeek 快速模型。
- 股票分析解释：DeepSeek 推理模型。
- 主决策：DeepSeek 推理模型。
- 风险复核：Claude，DeepSeek 作为备用。
- 一般报告：快速模型。

高风险决策才启用跨模型复核，避免每个 HOLD 都调用多个高成本模型。

## 8. risk-review-agent 详细设计

### 8.1 定位和边界

risk-review-agent是主决策与确定性硬风控之间的独立语义复核层。它负责发现主Agent可能忽略、误读或无法由静态规则表达的风险，但无权批准交易、修改RiskPolicy或创建订单。

职责包括：

- 独立检查原始证据，降低对主Agent结论的锚定。
- 验证建议中的关键事实是否有evidenceId支持、证据是否过期或相互冲突。
- 强制构造反方观点、下行情景和投资逻辑失效条件。
- 检查建议方向、目标仓位、持有期限与市场状态、流动性和当前组合是否一致。
- 对建议给出通过、有条件通过、拒绝或证据不足结论。
- 建议降低仓位、延迟观察、补充证据或增加退出条件，但不能直接修改原建议。

不负责：

- 计算和执行单票仓位、行业暴露、回撤、交易频次等硬规则。
- 用自然语言覆盖portfolio-risk-service的规则结果。
- 因模型“认为机会很好”而绕过数据新鲜度、人工审批或交易限制。

### 8.2 输入证据包

ContextBuilder生成不可变RiskReviewEvidencePacket，至少包含：

- 带proposalVersion的TradeProposal。
- 主Agent引用的全部ProvenanceRef，以及无法解析的evidenceId列表。
- DailyAnalysisSnapshot、FinancialNewsEvent、MarketRegimeSnapshot和MarketAnomalyEvent引用。
- 当前PortfolioSnapshot、组合暴露和可选的确定性预估指标。
- 各输入的DataFreshness、数据版本、Prompt版本和模型运行元数据。

风险复核默认只能读取主Agent当时可见的证据。若复核期间发现新事件，应创建新证据版本并触发新proposalVersion，不能静默加入旧建议。

### 8.3 复核流程

    RiskReviewActivity
      -> EvidencePacketValidator（确定性校验）
      -> IndependentEvidenceAssessment（先看证据，暂不看主结论）
      -> ProposalClaimComparison（逐项核对建议与证据）
      -> CounterThesisAndDownsideScenarios（反方论证和下行情景）
      -> RiskReviewSynthesis（结构化裁决）
      -> OutputValidator + AuditRecorder

为了控制低频系统的成本，上述步骤属于一个risk-review-agent的内部多阶段运行，不需要初期再常驻部署三个风险Agent。建议按风险分级：

- HOLD且未触发高风险事件：单模型轻量复核。
- BUY、SELL、显著调仓或HIGH事件：完整多阶段复核。
- CRITICAL事件、大仓位或模型分歧：使用不同Provider执行第二复核，再由确定性代码汇总两个结构化结果。

跨模型复核应优先使用不同模型家族，例如主决策使用DeepSeek、独立风险复核使用Claude。第二模型不可见第一模型的隐藏推理，只接收相同证据包和结构化结论；系统只保存可审计结论，不依赖或要求输出隐藏思维链。

### 8.4 输出和处置

输出必须符合[shared-contracts](./shared-contracts.md)中的RiskReviewResult：

- PASS：允许进入确定性硬风控，不代表交易最终通过。
- PASS_WITH_CONDITIONS：必须生成新proposalVersion落实条件并重新复核；不能直接进入执行。
- REJECT：终止当前版本，保存拒绝理由和证据。
- INSUFFICIENT_EVIDENCE：进入阻塞状态，等待数据刷新或人工处理；禁止按PASS降级。

推荐修改只能是建议值，例如maxPositionWeight、entryCondition、exitCondition或observationUntil。实际合法上限仍以portfolio-risk-service返回结果为准。

### 8.5 失败和降级

- EvidencePacket校验失败直接返回INSUFFICIENT_EVIDENCE，不调用模型补猜缺失事实。
- 主模型超时可切换已验证的备用Provider，但必须创建新的modelRunId并记录降级原因。
- 所有风险复核模型都不可用时，新增或加仓建议默认阻塞；减仓建议进入人工紧急处理，仍须硬风控。
- 两个复核模型结论冲突时按`REJECT > INSUFFICIENT_EVIDENCE > PASS_WITH_CONDITIONS > PASS`的阻断优先级确定性合并，riskLevel取最高级，并标记requiresHumanAttention。该顺序属于发布配置，变更必须版本化和回放测试。
- Prompt注入、无法解析的来源、过期行情或证据引用失败不得静默忽略。

### 8.6 开源参考与采用策略

- [TradingAgents](https://github.com/TauricResearch/TradingAgents)：主要参考Bull/Bear研究辩论、Aggressive/Neutral/Conservative风险视角以及Portfolio Manager分离设计。它是Python/LangGraph研究框架，只借鉴角色、测试样例和结构化流程，不作为生产硬风控或交易执行核心。
- [FinRobot](https://github.com/AI4Finance-Foundation/FinRobot)：参考财务风险评估、估值和投研报告的证据组织方式，适合补充长期基本面复核。
- [ai-hedge-fund](https://github.com/virattt/ai-hedge-fund)：参考Risk Manager与Portfolio Manager职责拆分，不直接复用其交易结论。
- [LangGraph.js](https://docs.langchain.com/oss/javascript/langgraph/overview)：只有当内部复核步骤、暂停点和分支明显复杂时，才可作为单个Temporal Activity内部的局部状态图；外层持久化工作流仍由Temporal负责。
- [Open Policy Agent](https://www.openpolicyagent.org/)：未来风险规则规模较大时可用于策略即代码，但归属portfolio-risk-service，不属于LLM Agent。

引入任何开源代码前必须单独检查许可证、版本、安全问题和数据源许可。开源项目生成的提示词和默认结果不能绕过本系统的Schema校验、证据追踪、硬风控和人工审批。

## 9. 记忆与审计

长期状态保存在 PostgreSQL，不依赖任何模型厂商的 Conversation 或 Store。

完整Memory分层、Context Manifest、主Agent历史检索、时间穿越防护、Decision Outcome和Strategy Memory治理见[Agent Memory设计](../agent-memory-design.md)。本服务只负责上下文构建、检索和运行审计，不成为行情、新闻、持仓、风险、建议或成交的第二事实来源。

每次调用记录：

- agentId、agentVersion、promptVersion。
- provider、model、endpointType。
- 输入快照版本和 evidenceIds。
- 工具调用及结果摘要。
- Token、延迟、重试和降级原因。
- 原始输出位置及校验后输出。

risk-review-agent还需记录proposalVersion、独立证据判断、逐项Claim检查、最终RiskReviewResult、跨模型分歧和确定性合并策略。原始模型文本只作为受限审计Artifact保存，业务状态仅使用校验后的结构化结果。

## 10. 安全与可靠性

- Prompt 中不放 API Key、数据库凭据和券商凭据。
- 工具按 Agent 白名单授权。
- 新闻、公告、研报和网页正文全部视为不可信数据，不能改变系统指令、工具权限或审批流程。
- 外部文本中的“调用工具”“忽略规则”等内容仅作为引用文本处理，关键工具调用必须由结构化策略和服务端授权决定。
- 模型超时和限流采用分 Provider 隔离。
- 同一次决策发生模型切换时生成新的 modelRunId 并完整审计。
- 对 Provider 上线前执行结构化输出、工具调用、流式、取消和异常契约测试。

## 11. 后续扩展

- 新增 Gemini、Qwen、GLM、Kimi、Bedrock、Vertex AI 和本地 vLLM。
- 引入模型评测集和按质量、成本动态路由。
- 增加 Prompt A/B，但生产决策只允许已发布版本。
- 将高成本推理 Worker 与快速 Worker 物理隔离。
- 增加影子模型，只记录结果不参与真实建议。
- 基于历史决策结果评估风险复核的漏报率、误拒率和校准度，但历史收益不能自动修改生产Prompt或RiskPolicy。

## 12. 验收标准

- 替换模型 Provider 不需要修改 Agent 业务定义。
- 所有 Agent 输出都通过 Schema 校验。
- 任意建议都能追溯到具体输入快照、新闻和模型调用。
- Agent 无法绕过工具白名单和硬风控直接创建订单。
- 风险复核的每个关键判断都引用证据或明确标记为假设。
- PASS_WITH_CONDITIONS不会直接进入硬风控或执行，必须形成新建议版本。
- 风险模型不可用、证据不足或跨模型冲突时不会静默放行新增仓位。
