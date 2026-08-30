# 01-04 CI、观测、安全运行说明

## CI 顺序

CI 固定执行 `lint`、`typecheck`、`test`、`test:contract`、`test:integration` 和格式检查。依赖锁文件必须同步提交；生成的契约通过 `check:generated` 防止漂移。

## 观测与安全

所有请求、事件和 Activity 使用 `correlationId`，可选传递 `causationId` 与 `traceparent`。日志必须调用共享 `log`，它会脱敏 Token、密码、数据库 URL、券商凭证、完整 Prompt 与受限新闻正文。`/live` 只表示进程存活；`/ready` 必须根据依赖状态返回 `UP` 或 `DOWN`。

指标使用 Prometheus 文本格式，至少包含 HTTP RED、数据库连接、NATS Lag、Outbox Lag 与 Temporal 活动失败。真实采集器、告警阈值和服务接入在各服务的 S5 阶段补充。

Secret 只通过 Docker Secret 或 CI Secret 注入；禁止 `.env`、日志、镜像层和 Git 历史出现凭证。CI 生成 SPDX SBOM，并以 Trivy 阻止 HIGH/CRITICAL 已修复漏洞进入主分支。
