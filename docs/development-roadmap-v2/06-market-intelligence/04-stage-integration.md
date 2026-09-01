# 06-04 市场情报阶段集成

## 目标

使用同一market-data DataVersion和Security Master验证三个服务的契约一致性，不接真实Agent。

## 实施步骤

1. 发布DataVersion，分别触发新闻实体映射Fixture、分钟回放和Regime日频计算。
2. 验证SecurityId、时区、availableAt、DataVersion和evidenceIds一致。
3. 用Fake Agent回写FinancialNewsEvent和异常/Regime解释结果，验证幂等契约。
4. 停止任一服务，其他两个仍可运行；平台暂不要求强同步聚合。
5. 对三类事件执行重复、迟到和重放。
6. 对盯盘批量快照验证`source`、`sourceChange`、Adapter/Schema版本、`quoteAgeSeconds`、覆盖率和质量状态可追溯；陈旧或失败窗口不得被新闻、Regime或Fake Agent解释为正常市场事实。

## 完成条件

三个服务均可独立运行，集成只通过API/事件/Artifact，不存在共享数据库或隐式代码依赖。
