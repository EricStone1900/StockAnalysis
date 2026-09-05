# research-automation-service测试计划

## Mac本地门禁

在仓库根目录执行：

```bash
./scripts/stage04-verify-mac.sh
```

脚本从`uv.lock`安装依赖，运行Ruff、Mypy、全部单元测试和集成测试。未配置`RESEARCH_AUTOMATION_DATABASE_URL`时，
PostgreSQL集成测试必须显示`skipped`，不得把跳过结果误记为数据库通过。

## 测试矩阵与Ubuntu门禁

| 类别 | Mac | Ubuntu |
|---|---|---|
| Domain/API/Hash/供应链 | 必须通过 | 必须通过 |
| PostgreSQL迁移、幂等、Outbox | 可跳过 | 必须通过 |
| MinIO/S3读写与Hash篡改 | Fake Adapter | 真实MinIO |
| Sandbox网络、Secret、宿主写入、资源限制 | 命令配置检查 | 真实容器执行 |
| quant独立复验与激活权限 | Fake Port | 独立服务账户/网络 |
| 研究服务故障不影响阶段03 | 单元契约 | Compose故障演练 |

Ubuntu必须固定Commit原生构建镜像，先执行迁移和健康检查，再执行`pytest tests/integration`及安全隔离脚本。任何
PIT、Hash、权限、隔离、幂等或恢复失败均为`FAIL`，不能用跳过、`xfail`或人工改写结果替代。

- Domain：实验和PromotionRequest状态机、预算和幂等。
- Sandbox：网络、文件、Secret、Docker Socket、超时、OOM和进程限制。
- Reproducibility：代码、依赖、镜像、数据、参数和随机种子。
- Model：Schema失败、超时、限流、Provider切换和成本上限。
- Supply Chain：SBOM、许可证、锁文件、镜像Digest和高危漏洞。
- Integration：quant独立复算、拒绝、批准和重复请求。
- Isolation：研究数据库用户不能写quant数据库，研究身份不能激活版本。

关键通过条件：任何自动生成代码都不能直接影响DailyAnalysisSnapshot或DailyStrategySnapshot。

## 纵向交付依赖调整

依据[ADR-020](../../architecture/adr/ADR-020-execution-consistency-and-delivery-gates.md)，本阶段增强能力不阻塞M1只读分析与M2隔离人工闭环；本阶段自身S0～S6、数据与安全测试及签署要求不变。验收应验证未启用本阶段时依赖方明确降级，不能伪造新闻、市场状态或学习结果；生产启用仍需原有门禁。
