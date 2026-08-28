# 04-03 Promotion Request与生产隔离

## 实施步骤

1. 研究服务只发布PromotionRequest：候选类型、Artifact、数据、评估摘要、风险和Hash。
2. quant-research-service使用独立身份、独立代码路径和独立数据复算候选。
3. 将PIT、样本外、成本、相关性、参数敏感度和安全检查作为硬门禁。
4. 人工批准后由quant服务创建新CANDIDATE版本；进一步验证后才能ACTIVE。
5. 保存请求、复验、拒绝、批准和版本关联的完整审计。

```text
RD-Agent Candidate
  -> Sandbox Evaluation
  -> PromotionRequest
  -> Independent Quant Reproduction
  -> Human Approval
  -> CANDIDATE
  -> Shadow/Validation
  -> ACTIVE
```

## 测试

- RD-Agent凭据调用activate接口返回403。
- 篡改Artifact Hash后复验拒绝。
- 重复PromotionRequest不创建重复版本。
- 研究服务停止不影响每日生产。

