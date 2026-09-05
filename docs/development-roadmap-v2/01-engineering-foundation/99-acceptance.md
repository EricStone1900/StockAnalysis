# 阶段01验收

- [ ] 两种语言模板均通过统一质量命令。
- [ ] 十二个微服务和Web项目骨架已创建。
- [ ] 每个微服务有独立Dockerfile、迁移、健康和版本端点。
- [ ] 每个写服务有Outbox/Inbox接入模板。
- [ ] PostgreSQL Database/User隔离已验证。
- [ ] NATS、Temporal、Redis、MinIO和OTel本地可用。
- [ ] 契约可以生成TypeScript与Python类型。
- [ ] CI、Secret扫描、SBOM和镜像扫描生效。
- [ ] 未提前实现领域业务。

只有全部通过才能进入market-data-service开发。

## 当前整改提交的验收范围

[整改记录](../../architecture/architecture-remediation-2026-09-05.md)为本次变更证据入口。历史人工PASS仅对应历史基线；本次未签署本阶段REAL_E2E/RELEASE。本地infra/research/manual-services/full-demo分组、配置缺失检查和不覆盖Secret；记录Mac资源实测。

- [ ] 补齐当前提交、镜像、迁移、契约版本与报告路径。
- [ ] 完成本阶段新增真实场景；授权、资金、幂等和恢复任一失败判FAIL。
- [ ] 记录风险、回滚目标和签署人，不以新增文档替代运行验证。
