# 阶段03：quant-research-service

## 目标

独立交付可复现的Qlib量化生产服务：股票池、因子、模型、回测、DailyAnalysisSnapshot和可扩展DailyStrategySnapshot。

领域基线见[量化服务](../../architecture/services/quant-research-service.md)与[日频策略平台](../../architecture/services/daily-strategy-extension-design.md)。

## 开发与交付环境

- 开发环境为Apple Silicon Mac。领域实现、Fixture计算、静态检查、单元测试、契约测试和必要的本地组件测试必须先在Mac完成。
- 最终验收环境为可通过SSH访问的Ubuntu服务器。服务器必须从固定Git提交和锁文件原生构建，执行完整Qlib、回测、快照、故障恢复与隔离Runner验证。
- 统一使用Python 3.12，并锁定Qlib、NumPy、PyArrow、LightGBM等计算依赖。阶段03不得使用当前模板中的Python 3.13。
- 不得把Mac的`.venv`、缓存、Docker数据卷、密钥或本地镜像目录复制到Ubuntu。若两端CPU架构不同，Ubuntu镜像必须在服务器原生构建。
- 文件SHA-256用于完整性校验；跨平台可复现性使用排序、定精度和规范序列化后的`canonicalContentHash`。模型指标按冻结容差比较，不要求ARM与x86模型文件逐字节相同。

## 顺序

1. [Qlib数据集、股票池与Factor Registry](./01-qlib-universe-factor.md)。
2. [评估、模型和回测](./02-evaluation-model-backtest.md)。
3. [每日分析快照](./03-daily-analysis-production.md)。
4. [策略Registry与Plugin SDK](./04-daily-strategy-platform.md)。
5. [Mac开发与Ubuntu交付](./05-mac-ubuntu-delivery.md)。
6. [测试](./90-test-plan.md)与[验收](./99-acceptance.md)。

## 边界

只输出量化事实、候选组合和策略快照，不生成TradeProposal、Approval或Order。Agent和Workflow尚未接入，全部调用用Fixture/Fake Consumer验证。

数据源接入属于阶段02的`market-data-service`。阶段03可先使用Fixture开发骨架和公式；真实数据验收必须使用阶段02按[首版数据源策略](../02-market-data-service/05-v1-data-source-policy.md)发布的固定DataVersion。历史估值、公告时间和修订链不完整时，价值与质量因子不得超过`DRAFT`。

## 收盘空洞的按需解释策略

阶段02停止继续写入快速模式全量对账。阶段03必须从固定父DataVersion读取`close_gap_index_uri`、`close_gap_index_hash`及原始Artifact Hash，并加载版本化的`CloseGapHandlingPolicy` Artifact；不得自行下载、删除、填充或改写Qlib价格。

首版策略固定为`assume_suspension_on_read`：对范围内每个`securityId + tradingDay`收盘空洞，确定性生成`SUSPENSION_ASSUMED`掩码，使其当日不可交易、不得计算依赖收盘价的收益率或价格因子；原始`close=NaN`保持不变。策略必须记录父DataVersion、空洞索引Hash、适用股票池、北交所排除规则、策略版本、审批引用、操作者和生成时间，并写入每个Run Manifest与输出Artifact。

该模式不生成或伪造BaoStock状态事实，不得称为`SUSPENSION_CONFIRMED`。运行质量必须继承为`WARN`：可用于阶段03开发、研究和`CANDIDATE`验证，但不得冻结为`PASS`数据结论、正式生产READY快照或替代精确状态验收。后续`exact`策略的供应商证据只能以新版本覆盖解释，不得改写历史Run。

Ubuntu未完成全部强制验收前，阶段03状态只能是`CANDIDATE`，不得冻结快照v1契约或进入阶段04。
