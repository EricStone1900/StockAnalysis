# research-automation-service验收

## Mac验证入口

```bash
./scripts/stage04-verify-mac.sh
```

本地通过只代表研究服务领域和契约切片可运行；PostgreSQL、真实MinIO、Sandbox容器隔离和跨服务权限必须在Ubuntu
完成后才能签署阶段04验收。

- [ ] 固定脚本最小实验闭环通过。
- [ ] RD-Agent Adapter和模型审计通过。
- [ ] Sandbox权限和资源隔离通过。
- [ ] Artifact可复现和Hash校验通过。
- [ ] PromotionRequest状态机和幂等通过。
- [ ] quant独立复算和人工批准边界通过。
- [ ] 研究身份不能修改或激活生产Registry。
- [ ] 服务故障不影响每日量化生产。
- [ ] 安全、许可证、SBOM和恢复Runbook完成。
