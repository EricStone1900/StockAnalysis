# market-monitor-service测试计划

- Calendar、Session、5分钟窗口、迟到和乱序聚合。
- Watchlist版本和候选/持仓合并。
- 每条异常规则的正常、阈值边界和极端场景。
- 去重、冷却、升级、恢复和Outbox重放。
- vn.py/Fake Gateway断线、重连和补发。
- River shadow、一致性、漂移和降级。
- 性能：目标Watchlist规模下持续交易时段资源基线。

历史回放是必选验收，不允许只使用实时手工测试。

