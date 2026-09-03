# research-automation-service验收

## Mac验证入口

```bash
./scripts/stage04-verify-mac.sh
```

本地通过只代表研究服务领域和契约切片可运行；PostgreSQL、真实MinIO、Sandbox容器隔离和跨服务权限必须在Ubuntu
完成后才能签署阶段04验收。

## 当前验收记录（人工确认）

截至2026-09-03，验收人确认阶段04已在Ubuntu服务器完成本手册要求的验证并全部通过。验证代码为当前提交
`8a0bffce39f06b301f4d16923749522031304d5b`。本记录依据验收人的人工确认；如未保存服务器原始日志、镜像Digest或
测试证据，应明确标记为人工确认，不能据此声称具备完整可复现审计能力。

| 字段 | 记录 |
|---|---|
| 验证Commit SHA | `8a0bffce39f06b301f4d16923749522031304d5b` |
| Ubuntu验证结论 | 验收人确认全部通过 |
| 验收结论 | `PASS（人工确认）` |
| 验收日期 | `2026-09-03` |
| 原始证据 | 以验收人实际保存情况为准 |

- [x] 固定脚本最小实验闭环通过。
- [x] RD-Agent Adapter和模型审计通过。
- [x] Sandbox权限和资源隔离通过。
- [x] Artifact可复现和Hash校验通过。
- [x] PromotionRequest状态机和幂等通过。
- [x] quant独立复算和人工批准边界通过。
- [x] 研究身份不能修改或激活生产Registry。
- [x] 服务故障不影响每日量化生产。
- [x] 安全、许可证、SBOM和恢复Runbook完成。
