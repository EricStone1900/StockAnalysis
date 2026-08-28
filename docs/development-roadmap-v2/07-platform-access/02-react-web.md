# 07-02 React Web

## 实施步骤

1. 建立TypeScript、路由、认证状态、Query缓存、错误边界和统一设计Token。
2. 第一页显示服务健康、DataVersion、快照新鲜度和最近任务状态。
3. 逐步增加量化候选/持仓分析、策略快照、Portfolio/Risk、新闻、异常和Regime页面。
4. 所有金额、时间、百分比和SecurityId使用统一格式组件。
5. STALE、PARTIAL和UNAVAILABLE必须显眼展示，不能与正常空数据混淆。
6. 高风险写操作预留确认、原因和幂等键，但阶段10以前不开放交易执行。

## 测试

- Component、路由、权限和错误边界。
- Mock Service Worker覆盖正常、过期、部分失败和403。
- 时区、Decimal显示、长文本和空状态。
- 基础无障碍和关键页面视觉回归。

