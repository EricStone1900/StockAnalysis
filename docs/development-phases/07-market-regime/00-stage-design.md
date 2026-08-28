# 阶段07：市场状态总设计

## 目标

在独立`services/market-regime-service`中实现趋势、宽度、波动、流动性和行业强弱的确定性计算，发布稳定、可解释的MarketRegimeSnapshot。

## 开发边界

市场状态不由LLM计算，不直接修改因子权重和RiskPolicy。Agent只解释快照。

## 实施要求

- 特征、阈值、权重和状态转换全部版本化。
- 使用迟滞和最短持续窗口控制抖动。
- 新定义先回放和影子运行，再批准ACTIVE。
- 数据FAIL时沿用旧状态并明确标记过期。
- 使用独立Database/User、Dockerfile和Outbox/Inbox，不写入market-data或quant-research数据库。

## 顺序文档

1. [市场和行业特征计算](./01-regime-features.md)
2. [Regime评分、迟滞和状态机](./02-regime-state-machine.md)
3. [历史回放、快照和Agent上下文](./03-regime-replay-agent-context.md)

## 阶段验收

- 数据FAIL不发布新状态。
- 普通单窗口不会导致状态频繁来回切换。
- 每次状态转换能解释输入和定义版本。
- 新定义经回放、影子运行和批准后才能ACTIVE。
