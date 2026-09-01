# market-monitor-service测试计划

- Calendar、Session、5分钟窗口、迟到和乱序聚合。
- Watchlist版本和候选/持仓合并。
- 每条异常规则的正常、阈值边界和极端场景。
- 去重、冷却、升级、恢复和Outbox重放。
- vn.py/Fake Gateway断线、重连和补发。
- River shadow、一致性、漂移和降级。
- 性能：目标Watchlist规模下持续交易时段资源基线。
- `FREE_TIERED_10_20_30`：一轮只发起一次批量请求并本地过滤50支；P0/P1/P2分别按10/20/30分钟评估且复用相同快照；80支需通过20个交易日、有效窗口成功率至少98%的稳定性验证后才能启用。
- 压力：100支P95窗口完成时间不超过120秒；限流、超时、字段漂移、覆盖不足、行情超过180秒及连续两轮失败均告警并失败关闭。
- 恢复：Provider熔断、退避、批准的备用Adapter切换和`sourceChange`审计；禁止同一窗口静默混合来源。
- 策略：MonitorPolicy在交易时段冻结；阈值动作只允许HOLD、WATCH、DELAY、CANCEL、风险减仓或执行修正，不能重新计算日频Alpha。

历史回放是必选验收，不允许只使用实时手工测试。
