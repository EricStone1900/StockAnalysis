# 09-01 四个专业Agent

## 实施顺序

### 1. stock-analysis-agent

读取DailyAnalysisSnapshot、ACTIVE DailyStrategySnapshot和Portfolio摘要，解释候选/持仓、策略共识、冲突与NO_TRADE基线。禁止计算新因子、扩大股票池或运行插件。

### 2. financial-news-agent

读取NewsEventCandidate和证据Tool，区分事实与推测，输出影响方向、强度、期限、来源冲突和置信度。正文始终是不可信内容。

### 3. market-monitor-agent

只读取MarketAnomalyEvent，输出IGNORE/WATCH/REASSESS/RISK_ESCALATION，不接连续Tick、不发止损单。

### 4. market-state-agent

读取MarketRegimeSnapshot和组合暴露，解释市场/行业影响，不计算Regime、不修改RiskPolicy。

统一输出骨架：

```ts
interface SpecialistAssessment {
  assessmentId: string;
  agentRunId: string;
  summary: string;
  opportunities: string[];
  risks: string[];
  evidenceIds: string[];
  confidence: number;
  validUntil: string;
}
```

## 步骤

每个Agent先Fake Provider契约，再Golden Fixture，再DeepSeek测试环境，最后接真实只读Tool。

