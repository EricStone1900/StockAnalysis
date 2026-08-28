# 阶段05：新闻情报总设计

## 目标

在独立`services/news-intelligence-service`中建立新闻和公告的采集、证据保存、去重、股票实体关联及结构化事件分析闭环。

## 开发边界

新闻服务负责数据处理和事实所有权；模型调用通过统一Agent运行时接口，不能从新闻情绪直接生成订单。

## 实施要求

- 原文始终按不可信内容处理。
- 来源许可、留存和删除策略必须保存。
- 去重后不能丢失任何来源证据。
- 本阶段使用Fake分析Port完成闭环，真实Agent在阶段08接入。
- 使用独立Database/User、Dockerfile和Outbox/Inbox；通过NATS发布候选与完成事件。

## 顺序文档

1. [来源采集、正文和证据存储](./01-source-ingestion-evidence.md)
2. [去重、聚类和实体关联](./02-dedup-entity-linking.md)
3. [财经新闻Agent与事件发布](./03-news-agent-event-publish.md)

## 阶段验收

- 接入官方公告和至少两个财经来源。
- 同一转载事件只形成一个候选事件。
- 事件可追溯全部原文和许可元数据。
- 来源故障和过期状态对调用方可见。
