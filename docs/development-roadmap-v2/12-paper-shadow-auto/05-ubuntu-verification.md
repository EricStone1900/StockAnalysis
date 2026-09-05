# 阶段12 Ubuntu 人工验证步骤

本清单用于在 Ubuntu 服务器上复核已在 Mac 完成的代码。服务器只使用测试数据库、隔离账户和模拟 Broker；本阶段未获得独立风险批准前，不得填入生产凭证或执行真实订单。

## 1. 获取并固定代码

```sh
git clone https://github.com/EricStone1900/StockAnalysis.git
cd StockAnalysis
git fetch origin
git checkout origin/main
git rev-parse HEAD
git status --short
```

记录 `git rev-parse HEAD` 输出。`git status --short` 应为空，确保验收对应唯一提交。

## 2. 安装依赖并执行本地同款检查

```sh
corepack enable
pnpm install --frozen-lockfile
pnpm --filter @stock/trade-execution-service lint
pnpm --filter @stock/trade-execution-service typecheck
pnpm --filter @stock/trade-execution-service test -- --run
git diff --check
```

这些检查验证 Linux 环境下的依赖、编译和测试结果与 Mac 一致；任一失败都停止后续人工验收。

## 3. 复核隔离边界

确认测试环境的账户名、数据库和网络地址均为隔离值，例如 `paper-*` 与测试 PostgreSQL。检查 Compose、环境变量和日志中没有生产券商 URL、令牌或账户号。Shadow 只允许写入 Shadow Ledger，不能出现 `place/cancel` 的真实网络调用。

## 4. 执行四类核心演练

逐项运行单元测试或等价手工请求，并保存终端输出：

1. Paper：同一个 `clientOrderId` 重复提交只产生一个结果；部分成交、费用、滑点和不可交易标的均有明确状态。
2. Shadow：使用迟到市场数据时返回 `FUTURE_MARKET_DATA`；不可交易返回差异；重复决策返回相同 `contentHash`，且无 Broker 写调用。
3. 自动执行：非白名单账户、超出单笔/批次额度、交易时段外、审批/风险/预算缺失和价格偏差均在下单前拒绝。
4. UNKNOWN：让测试 Broker 返回未知状态，确认只调用一次 `place`，再次提交返回相同 `UNKNOWN`，没有自动重下。

## 5. Kill Switch 演练

依次启用全局、账户、策略和标的暂停，确认新增订单同步拒绝；清除后仅允许符合其他门禁的订单。再让 Kill Switch 控制面读取失败，确认系统拒绝下单（fail-closed）。记录每次操作的时间、原因和结果。

## 6. 验收记录与回滚

将提交 SHA、命令输出摘要、失败项、风险和回滚提交写入验收记录。若失败，立即关闭自动执行开关，仅保留 Paper/Shadow，恢复到上一已验收 SHA；不得补发故障期间的旧订单。人工确认全部通过后，才可进入独立风险审批和小资金白名单评审。
