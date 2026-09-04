# news-intelligence-service验收

状态：PASS（随阶段06 Ubuntu 人工验收通过，基线 `f43a7cd`）

- [ ] 独立部署、采集和证据最小切片通过。
- [ ] 来源许可和Provenance可追溯。
- [ ] 多层去重和实体关联通过。
- [ ] Candidate发布和Fake Agent回写契约通过。
- [ ] 重复、迟到、来源故障和Artifact恢复通过。
- [ ] 不可信正文不能扩大权限。
- [ ] 服务不生成TradeProposal或修改股票池。

## 当前实现证据

- 已实现提交：`8b05d9d`、`c010b81`、`68fdb3e`、`954c098`、`3183ec3`、`f28be33`、`8d69253`、`c364255`、`e7547d1`、`1943bd6`、`83af77e`。
- 本机质量门禁：Ruff、Mypy、`git diff --check`通过；新闻服务单元测试16项通过，PostgreSQL集成测试1项通过。
- 已覆盖：采集幂等、证据Hash、许可拒绝、实体歧义拒绝、Candidate/Fake Analyzer契约、事件查询、新鲜度、限流和来源故障关闭。
- 尚待人工验收：Compose完整启动、真实MinIO对象读回、真实HTTP鉴权/日志脱敏、跨服务事件发布及Ubuntu部署恢复测试。

人工验收必须在目标Ubuntu环境执行；未完成项目不得将本服务标记为阶段PASS。
