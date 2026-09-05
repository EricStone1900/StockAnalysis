# 阶段01测试计划

## 自动测试

- 所有Node和Python服务模板执行统一lint、typecheck、unit、contract命令。
- 每个服务执行Docker build、迁移、live/ready/metrics/version测试。
- PostgreSQL用户隔离、Outbox恢复、Inbox重复、NATS DLQ和Temporal恢复。
- OpenAPI/AsyncAPI生成漂移和破坏性变化检查。
- 日志Secret扫描、SBOM和镜像漏洞扫描。

## 组件场景

1. 只启动基础设施和任意一个空服务，Readiness通过。
2. 停止NATS，写入Outbox成功；恢复后事件发布。
3. 清空Redis，服务事实无变化。
4. 重启Temporal Worker，测试Workflow继续。
5. 尝试用A服务账号写B服务数据库，权限拒绝。

通过标准：所有项目独立通过，不能只验证整套Compose一起运行。


## ADR-020新增测试门禁

本地infra/research/manual-services/full-demo分组、配置缺失检查和不覆盖Secret；记录Mac资源实测。

专项执行：在仓库根配置隔离数据库后运行`bash scripts/verify-execution-hardening.sh`。该命令只覆盖执行/工作流代码和PostgreSQL专项，不代替本阶段其余测试。真实E2E需保留请求、数据库、事件、Worker证据；记录跳过项，禁止视为PASS。
