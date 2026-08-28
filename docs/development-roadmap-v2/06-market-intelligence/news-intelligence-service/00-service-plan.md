# news-intelligence-service开发计划

## 目标

建立许可可追溯的新闻采集、证据归档、去重、实体关联和候选事件闭环。领域基线见[新闻服务设计](../../../architecture/services/news-intelligence-service.md)。

## 内部阶段

1. [骨架、采集与证据最小切片](./01-scaffold-ingestion.md)。
2. [去重、实体、Agent契约和强化](./02-core-integration-hardening.md)。
3. [测试](./90-test-plan.md)与[验收](./99-acceptance.md)。

真实financial-news-agent推理不在本阶段实现，只验证请求/回写契约和Fake结果。

