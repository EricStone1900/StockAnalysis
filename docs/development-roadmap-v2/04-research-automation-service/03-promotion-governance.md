# 04-03 Promotion Request与生产隔离

## 当前最小切片

已实现`PromotionRequest`及其`REQUESTED -> REPRODUCED / REJECTED`状态机。请求绑定候选Manifest内容Hash、风险摘要和
幂等键；独立复验必须返回PIT、样本外、成本、相关性、参数敏感度和安全六项门禁结果，任一失败即拒绝。研究服务没有
approve、activate或写入quant Registry的方法；人工批准和创建新CANDIDATE版本只能由quant服务独立身份完成。

当前请求仓储为内存实现，用于本地契约测试；请求、复验、拒绝和批准审计的PostgreSQL持久化、跨服务签名和真实权限
验证属于后续组件集成。现已增加`research_promotion_requests`与幂等键表，保存请求、风险、Manifest、门禁结果和拒绝原因；
真实环境仍需由quant服务执行独立复验、人工批准和版本创建。研究服务停止不应影响阶段03每日生产链路。

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
