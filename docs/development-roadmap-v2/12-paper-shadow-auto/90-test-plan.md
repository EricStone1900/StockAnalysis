# 阶段12测试计划

## 当前本地实现与命令

阶段12当前已实现 Paper、Shadow、受控自动执行门禁和独立 Kill Switch 的最小纵向切片。Mac 本地执行：

```sh
pnpm --filter @stock/trade-execution-service lint
pnpm --filter @stock/trade-execution-service typecheck
pnpm --filter @stock/trade-execution-service test -- --run
git diff --check
```

测试必须确认：Paper 不污染真实账本；Shadow 仅产生 `episodeType=SHADOW` 的理论报告；未来市场数据、不可交易标的和缺失数据不得模拟成交；自动执行在下单前完成白名单、策略版本、审批、风险、预算、时段、价格和额度校验；Broker 返回 `UNKNOWN` 后不得自动重试；Kill Switch 读取异常必须 fail-closed。

## Ubuntu 人工验证门禁

Ubuntu 上只使用隔离测试账户和测试数据库，不配置生产券商凭证。完整步骤见 [05-ubuntu-verification.md](./05-ubuntu-verification.md)。人工验收至少保留：代码提交 SHA、镜像构建结果、测试输出摘要、Kill Switch 演练结果和回滚说明。

- Paper成交、费用、滑点、部分成交和不可交易。
- Paper多Leg批次、每日0～2批、第二批reason和预算状态。
- Shadow无写权限、PIT成交模拟、五类联合对照和策略账本隔离。
- Broker Contract、认证、限流、断线、UNKNOWN、乱序和重复回报。
- 下单前全部版本、新鲜度、白名单、价格、预算预留和批次检查。
- Kill Switch各层级、独立故障和恢复。
- Paper/Shadow/生产数据库、Secret和网络隔离。
- 日终对账、灾难恢复、Secret轮换和审计。
- 小资金上线前长周期容量、错误率、滑点和回撤报告。

任何UNKNOWN重复下单、同批拆分绕过预算、跨环境污染或Kill Switch失效都判定FAIL。
