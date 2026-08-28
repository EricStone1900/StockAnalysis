# news-intelligence-service

## 1. 定位

独立的财经新闻情报微服务，负责新闻、公告和媒体信息的采集、正文标准化、去重、股票实体关联和结构化金融事件生成。

财经新闻 Agent 消费本服务结果，不直接维护爬虫或新闻数据库。

推荐技术栈：Python、FastAPI、FinNLP、AKShare、自建 RSSHub、PostgreSQL、pgvector、S3/MinIO。模型调用统一交给 agent-runtime-service，避免在 Python 新闻服务中再维护一套模型网关。

## 2. 数据源优先级

    交易所和巨潮公告
      -> 公司官方公告
      -> 主流财经媒体
      -> 一般新闻媒体
      -> 社交媒体和自媒体

来源优先级同时影响 sourceReliability，但不能替代具体内容核验。

## 3. 内部架构

    Source Adapters
      -> Raw News Store
      -> Content Extractor
      -> Normalizer
      -> Exact Deduplicator
      -> Near-Duplicate Cluster
      -> Entity Linker
      -> Event Candidate Builder
      -> Analysis Queue
      -> FinancialNewsEvent Repository
      -> Query API

推荐 Provider：

- FinNLPProvider。
- AkShareProvider。
- RssHubProvider。
- CninfoProvider。
- ExchangeAnnouncementProvider。
- CommercialNewsProvider，未来扩展。

## 4. 新闻标准结构

NewsItem 至少包含：

- newsId、source、sourceType、sourceUrl。
- title、content、language。
- publishedAt、fetchedAt、availableAt。
- contentHash、canonicalUrl。
- mentionedSymbols。
- status：RAW、PROCESSED、DUPLICATE、FAILED。
- licenseMetadata 和 retentionPolicy。

原始正文写入对象存储，数据库保存标准字段、摘要和 Artifact 引用。

## 5. 去重与事件聚类

按顺序执行：

1. canonical URL 去重。
2. 标题和正文 Hash 去重。
3. SimHash/MinHash 近似去重。
4. 向量相似度聚类。
5. 根据时间窗、公司和事件类型合并同一事件。

多个转载新闻先合并为一个 NewsEventCandidate。Temporal 随后调用 agent-runtime-service 中的 financial-news-agent，只分析一次并将 FinancialNewsEvent 写回本服务，同时保留全部来源证据。

## 6. 实体关联

Entity Linker 使用 market-data-service 的 Security Master：

- 股票代码。
- 公司全称和简称。
- 曾用名。
- 子公司、品牌和核心产品。
- 控股股东和关键管理人员。

实体关系带 confidence；低置信度结果不直接进入重要事件列表。

## 7. 结构化金融事件

事件字段至少包含：

- eventId、newsIds、eventType。
- affectedSymbols 和 relevance。
- impactDirection：POSITIVE、NEGATIVE、NEUTRAL、UNCERTAIN。
- impactMagnitude：LOW、MEDIUM、HIGH。
- impactHorizon：INTRADAY、SHORT_TERM、MEDIUM_TERM。
- noveltyScore、sourceReliability、confidence。
- summary、reasoning、evidenceIds。
- occurredAt、publishedAt、analyzedAt。
- provider、modelId、promptVersion。

事件类型包括业绩、指引、并购、股东变化、监管、诉讼、合同、产品、管理层、分红、回购、行业和宏观。

## 8. 与财经新闻 Agent 的协作

    news-intelligence-service 采集、清洗、去重和聚类
      -> 发布 NewsEventCandidate
      -> Temporal 调用 financial-news-agent
      -> DeepSeek 完成中文事件提取和初步影响分析
      -> 高影响或来源冲突时可由 Claude 复核
      -> Agent Kernel 执行 Schema 与证据校验
      -> 将 FinancialNewsEvent 写回 news-intelligence-service

本服务可以使用规则或本地小模型完成语言检测、垃圾过滤和基础分类，但不直接维护 DeepSeek、Claude 等远程模型 Provider。模型不能把新闻情绪直接转换成交易指令。

## 9. API

读取接口：

- GET /api/v1/news
- GET /api/v1/news/{newsId}
- GET /api/v1/events
- GET /api/v1/events/important
- GET /api/v1/stocks/{symbol}/news
- GET /api/v1/stocks/{symbol}/events
- GET /api/v1/stocks/{symbol}/news-summary
- GET /internal/v1/event-candidates/pending

任务接口：

- POST /internal/v1/jobs/collect
- POST /internal/v1/event-candidates/{candidateId}/analysis-result
- POST /internal/v1/jobs/reprocess
- GET /internal/v1/jobs/{runId}

所有查询返回 latestCollectedAt、latestAnalyzedAt、isStale 和 sourcesStatus。

## 10. 调度

- 全量新闻分析：每 12 小时。
- 候选股和持仓股：更短周期增量采集。
- 交易所公告：事件或短周期轮询。
- 重大新闻：发布事件以触发 InvestmentDecisionWorkflow。
- 同一新闻处理任务通过 contentHash 和 sourceRecordId 幂等。

## 11. 可靠性与合规

- 每个 Provider 独立限流、熔断和健康检查。
- 单一爬虫故障不阻止其他来源更新。
- 优先使用官方 API、官方公告和合法 RSS。
- 保存内容来源、许可范围和删除策略。
- 对不允许长期保存全文的来源，只保存结构化字段和必要引用。
- robots、登录态和反爬变化不得通过绕过安全机制解决。
- 原始正文标记为untrustedContent，传给Agent时与系统指令和工具描述严格分隔。

## 12. 后续扩展

- 接入付费商业新闻源和全球新闻。
- 增加研报、电话会、互动问答和监管问询。
- 建立公司知识图谱。
- 训练本地财经分类和情绪模型，减少大模型调用。
- 建立新闻影响回测，评价方向、强度和时间范围预测。
- 增加来源可信度和传播路径模型。

## 13. 验收标准

- 相同转载新闻不会反复触发模型和决策工作流。
- 重要事件能够追溯到原文和来源。
- Provider 故障时 API 明确返回 freshness 和来源状态。
- 新闻 Agent只消费结构化事件，不依赖具体采集框架的数据格式。
