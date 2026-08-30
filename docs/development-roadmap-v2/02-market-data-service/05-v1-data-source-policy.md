# 02-05 首版数据源与PIT补全策略

## 目标与版本决策

正式版v1以[`chenditc/investment_data`](https://github.com/chenditc/investment_data)发布的A股Qlib日频数据为主数据源，Tushare及其他来源仅用于补充、校验和修订追踪。该决策只适用于首版日频研究，不代表已获得底层数据的再分发权；上线前必须逐项记录来源、许可范围、署名要求和使用限制。

量化服务不得直接调用任何第三方SDK。所有来源统一由`market-data-service`采集、固化为不可变原始Artifact、标准化并发布新的DataVersion，`quant-research-service`只读取DataVersion及其Qlib Artifact。

## 来源职责与优先级

| 来源 | v1职责 | 使用原则 |
|---|---|---|
| `investment_data` | 日线OHLCV、成交额、复权后Qlib主数据 | 固定Release Tag、归档和Manifest，不使用浮动`latest` |
| [BaoStock](http://baostock.com/) | PE/PB/PS/PCF、交易状态、ST及基础财务指标补充 | 只补缺或校验，不静默覆盖主数据 |
| [AKShare](https://akshare.akfamily.xyz/) | 财务报表、公告日期和多来源交叉校验 | 保存实际底层来源和抓取时间；接口变化必须触发告警 |
| [巨潮资讯（CNINFO）](https://www.cninfo.com.cn/new/index) | 公告、更正公告和修订证据的权威原文 | 原文作为不可变Artifact；结构化抽取结果必须可追溯 |
| [Tushare Pro](https://tushare.pro/document/2) | 可选的结构化财务修订、公告时间和交叉校验 | 受积分、授权和调用配额约束，不得成为无授权环境的硬依赖 |

主数据字段正常时优先采用`investment_data`；补充源只能填补明确缺失的字段。来源冲突不得直接覆盖，必须生成对账结果，按字段记录原值、候选值、来源、差异阈值和处置结论。任何修复、口径变化、来源切换或Release升级都发布新DataVersion。

## 数据契约与PIT规则

每条标准记录除现有字段外，还要保存`sourceReleaseTag`或`sourceVersion`、`rawArtifactUri`、`rawArtifactHash`、`licenseRef`及字段级`provenance`。财务事实至少包含：

- `periodEnd`：报告期结束日，禁止作为历史可见时间。
- `announcedAt`：首次公开披露时间。
- `availableAt`：系统允许研究任务读取该事实的保守时间。
- `revision`、`revisionReason`和`supersedes`：修订序号、原因及被替代记录。

同一事实值发生变化时追加修订版本，不覆盖旧值。若来源只有公告日期而没有时刻，`availableAt`默认设为公告日之后的下一可交易时点；具体截止规则必须版本化。所有回测查询强制满足`availableAt <= asOf`。

## 导入与发布流程

1. 解析固定Release Tag，下载归档及Manifest并校验格式、大小和Hash。
2. 将原始文件写入MinIO不可变路径；重复导入同一来源版本必须幂等。
3. 标准化证券、日历、行情、估值、财务和公告事实，保留字段级来源。
4. 执行交易日、复权、停牌、缺失、异常值和跨来源差异检查。
5. 隔离超阈值冲突；质量为`FAIL`时禁止发布。
6. 生成标准Parquet和Qlib Artifact，发布带策略版本与质量报告的DataVersion。

## 实现状态与后续任务

当前阶段02已具备Fixture Adapter、Artifact Hash校验、基本PIT/质量门禁、DataVersion与发布事件。本轮还完成了来源、字段Provenance与财务修订的领域契约、数据库迁移、纯领域对账规则，以及固定`investment_data` Release的下载/Manifest校验、MinIO不可变落地、来源策略/原始Artifact持久化、结构与Qlib日频质量报告和DataVersion发布应用服务。Qlib扫描已检查日历、股票池、OHLCV覆盖、浮点范围和可对齐样本；停牌与缺失的最终区分仍需要交易状态补充源。真实Release尚未进行人工导入验收，调度入口和字段级事实写入也尚未接通。以下未完成项不得因本文存在而视为已完成：

| 待实现项 | 最迟门禁 | 完成标志 |
|---|---|---|
| `InvestmentDataReleaseAdapter`真实Release导入与验收 | 阶段03真实数据验收前 | 固定Release可幂等导入，损坏归档被拒绝 |
| [BaoStock交易状态与ST补充](./07-baostock-status-st-enrichment.md) | 阶段03真实数据验收前 | 收盘空洞逐条对账、PIT与来源证据测试通过 |
| BaoStock估值和财务Adapter | 价值/质量因子转`CANDIDATE`前 | 覆盖率、限流、重试和来源证据测试通过 |
| AKShare/CNINFO公告与修订Adapter | 质量因子转`CANDIDATE`前 | 公告原文Hash、披露时间和修订链可追溯 |
| Tushare Pro可选Adapter | 获得合法Token后 | 未配置时明确降级，配置后可对账且Secret不落盘/日志 |
| 字段级Provenance与对账结果的持久化写入、质量报告扩展及来源切换发布集成 | 阶段03真实数据验收前 | 冲突不静默覆盖，来源切换产生新DataVersion |
| 财务Revision Ledger的真实导入、持久化查询及保守`availableAt`规则 | 价值/质量因子转`CANDIDATE`前 | PIT、更正公告和未来数据测试全部通过 |
| 许可、配额、限流、漂移监控与Runbook | 正式版发布前 | 许可清单、告警、恢复和回滚演练有证据 |

## 后续实施顺序

1. 先冻结来源、Provenance、Revision和质量报告契约，并增加数据库迁移；这是所有真实Adapter的共同前置。
2. 实现`InvestmentDataReleaseAdapter`、原始Artifact落地、Manifest校验和Qlib标准化，先让价格类因子使用固定真实DataVersion完成闭环。
3. 实现字段级对账、冲突隔离、来源策略版本和跨来源测试，避免补充源接入后改变既有数据口径。
4. 依次接入BaoStock估值/状态、AKShare/CNINFO公告与修订；Tushare Pro保持可选，用于合法授权环境下的结构化复核。
5. 补齐财务Revision Ledger、PIT覆盖率门禁、限流/漂移告警、许可清单和恢复Runbook，再开放价值与质量因子的真实数据准入。

阶段03的服务骨架、Fixture股票池和价格因子代码可以先开发，但真实数据端到端验收必须等待第1～3步完成。价值和质量因子可以先实现公式与Fixture测试，其状态必须等待第4～5步完成后才能超过`DRAFT`。

## 北交所暂时排除策略

首期`BaoStock`交易状态补充仅覆盖沪深普通A股。派生研究范围使用`CN_A_EQUITY_EX_BSE`：沪市仅纳入`600`、`601`、`603`、`605`、`688`前缀，深市仅纳入`000`、`001`、`002`、`003`、`300`、`301`前缀；指数、基金/ETF、B股及北交所均不进入首期股票池。质量报告分别记录BSE与非普通股空洞的排除数量；原始`investment_data`归档不删除、不修改。北交所必须保持范围降级，直至接入可验证的状态来源并完成同等PIT、Provenance与对账验收。

## 阶段03准入规则

价格动量、波动率和流动性因子可在主日频DataVersion通过质量门禁后进入候选验证。价值因子必须同时具备历史估值口径与可用时间验证；质量及财务修订类因子必须具备公告时间、修订链和PIT覆盖。在补充能力未完成前，这些因子只能保持`DRAFT`或使用明确标注的Fixture验证，不得进入`ACTIVE`生产FactorSet。
