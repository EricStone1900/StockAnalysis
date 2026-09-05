# 阶段04：research-automation-service

## 目标

独立交付RD-Agent自动研究通道，在隔离环境生成因子、模型和策略候选，但不进入每日生产链路且不能激活生产Registry。

领域基线见[自动研究服务](../../architecture/services/research-automation-service.md)。

## 顺序

1. [实验骨架与Sandbox最小切片](./01-experiment-sandbox.md)。
2. [RD-Agent、Artifact与可复现研究](./02-rd-agent-artifacts.md)。
3. [Promotion Request与生产隔离](./03-promotion-governance.md)。
4. [测试](./90-test-plan.md)与[验收](./99-acceptance.md)。

## 门禁

研究身份没有quant生产Registry写权限；候选失败不能影响阶段03每日生产；所有实验有预算、Hash、依赖锁和可复现记录。


## 纵向交付依赖调整

依据[ADR-020](../../architecture/adr/ADR-020-execution-consistency-and-delivery-gates.md)，本阶段增强能力不阻塞M1只读分析与M2隔离人工闭环；本阶段自身S0～S6、数据与安全测试及签署要求不变。验收应验证未启用本阶段时依赖方明确降级，不能伪造新闻、市场状态或学习结果；生产启用仍需原有门禁。
