# quant-research-service测试计划

## 双环境门禁

| 测试层 | Mac | Ubuntu |
|---|---|---|
| Ruff、Mypy、Domain/Application单元测试 | 必须 | 必须复验 |
| OpenAPI、AsyncAPI、Plugin Schema契约 | 必须 | 必须复验 |
| Fixture PIT、因子、模型基线、回测、快照E2E | 必须 | 必须复验 |
| PostgreSQL、MinIO、NATS组件集成 | 必须 | 必须 |
| 原生Qlib完整计算与资源限制 | 可做冒烟 | 最终门禁 |
| Runner网络/Secret/只读/OOM隔离 | 可做基础验证 | 最终门禁 |
| 故障恢复、旧READY降级和大数据性能 | 可做Fixture验证 | 最终门禁 |

Mac执行：

```bash
./scripts/stage03-verify-mac.sh
./scripts/stage03-record-evidence.sh artifacts/stage03/mac
```

Ubuntu执行：

```bash
./scripts/stage03-verify-ubuntu.sh
./scripts/stage03-record-evidence.sh artifacts/stage03/ubuntu
```

两个脚本必须使用同一个Commit SHA、Fixture DataVersion和契约版本。测试脚本返回非零即判定失败，不允许通过忽略、`xfail`或临时放宽容差完成验收。

## 测试矩阵

- 因子：PIT、股票池、生存偏差、缺失、极值、中性化和可复现。
- 模型：时序切分、泄漏、随机种子、样本外和漂移。
- 回测：信号/成交时间、成本、滑点、停牌、涨跌停和最低费用。
- 快照：原子发布、失败保旧、重复任务、Hash和新鲜度。
- 策略：Plugin Contract、NO_REBALANCE、最低持有期、换手、容量和Ensemble。
- 安全：隔离Runner、SBOM、许可证、超时、OOM和恶意输出。
- 契约：OpenAPI、事件、Artifact引用和跨语言Schema。
- 数据来源：固定Release、输入Hash、来源策略版本、字段级Provenance和许可引用。
- 因子准入：价格类与价值/质量类分别门禁，缺少估值或财务PIT时禁止错误晋级。

关键Fixture必须覆盖牛市、震荡、下跌、极端波动、停牌和数据缺口。

按需缺口解释Fixture还必须覆盖：同一空洞索引重复生成相同掩码；掩码股票日不可交易且不产生收益率/价格因子；原始`NaN`不被改写；索引或策略Artifact Hash不匹配失败；北交所排除范围不被错误纳入；`WARN`质量、审批引用与策略版本进入Run Manifest。不得通过把缺口填为零、前值或伪造BaoStock状态使测试通过。

## 真实日频数据验证

正式验收选择一个固定`investment_data` Release，由`market-data-service`先导入并发布DataVersion。测试记录必须包含Release Tag、归档与Manifest Hash、交易日范围、证券数、行数、缺失率、补充率、冲突率及质量报告引用。

- 使用同一DataVersion在Mac和Ubuntu各执行两次价格类因子，`canonicalContentHash`必须稳定且跨平台一致。
- 随机抽样交易日、停牌、ST和复权事件，对比标准Parquet、Qlib表达式输入和因子输出。
- 删除估值补充数据后执行价值因子Promotion，预期被门禁拒绝；恢复合格数据后再验证覆盖率与PIT。
- 删除公告时间或修订链后执行质量因子Promotion，预期被拒绝；更正公告前后的`asOf`结果必须分别使用旧值和新值。
- 补充源不可用时，价格类验证可按已记录范围继续；受影响的价值/质量因子必须保持`DRAFT`并输出明确原因。

## 跨平台结果对比

对比Mac和Ubuntu证据目录中的输入Artifact SHA-256、`canonicalContentHash`、Universe/FactorSet/Model/CostModel版本、快照行数和冻结业务指标。输入Hash或规范内容Hash不同直接判定`FAIL`；模型指标只允许使用版本化验收配置中预先定义的绝对/相对容差。
