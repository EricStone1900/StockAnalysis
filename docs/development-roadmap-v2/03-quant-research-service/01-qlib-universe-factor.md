# 03-01 Qlib、股票池与Factor Registry

## 实施步骤

1. 从Python 3.12模板建立服务，使用`uv.lock`冻结Qlib及数值计算依赖；Adapter只读取market-data发布的不可变DataVersion Artifact，禁止直接调用`investment_data`、BaoStock、AKShare、CNINFO或Tushare。
2. 建立版本化`CloseGapHandlingPolicy`与确定性停牌掩码：验证父DataVersion、`close-gap-index` Hash和策略Artifact后，按`assume_suspension_on_read`将收盘空洞排除出当日可交易股票池、收益率和价格因子计算；不得填价或查询第三方来源。
3. 建立历史股票池快照，纳入上市天数、ST、停牌、流动性和退市样本规则。
4. 建立FactorDefinition、FactorVersion、FactorSet Aggregate和DRAFT/CANDIDATE/ACTIVE状态。
5. 首批实现价格动量、波动率、流动性、价值和质量基础因子。
6. 统一缺失值、去极值、标准化和行业/市值中性化版本。
7. Qlib表达式封装在Adapter，不泄漏到Domain和跨服务DTO。
8. 因子明细按`securityId + tradingDay + factorId`稳定排序、固定Decimal/浮点精度并规范序列化，生成跨Mac与Ubuntu比较的`canonicalContentHash`；Parquet文件另存Artifact SHA-256。

## S0：冻结的按需空洞解释契约

本服务只接收`MarketDataVersionRef`：`versionId`、原始Qlib Artifact URI/SHA-256、
`closeGapIndex` URI/SHA-256、来源Release、来源策略版本和阶段02质量结论。读取 Adapter 必须先校验
两个对象的 SHA-256；Hash 不一致、索引不属于该原始 Artifact、DataVersion 未固定或质量为`FAIL`时立即失败。

`CloseGapHandlingPolicy`是单独、不可变的 Artifact，至少包含`policyVersion`、`mode`、适用股票池版本、
北交所排除开关、审批引用、确认操作者与UTC审批时间。首版只接受`assume_suspension_on_read`；不得接受
未审批的自由文本策略，也不得声明`SUSPENSION_CONFIRMED`。

输出为稳定排序的`SuspensionMaskEntry(securityId, tradingDay)`，状态固定为`SUSPENSION_ASSUMED`。
其规范内容Hash仅由输入DataVersion/索引/策略Hash、适用范围和条目决定，不包含运行时间。原始`close=NaN`
不写回；掩码只禁止该股票日交易、收益率和价格类因子计算。Run Manifest必须保存所有上述引用和`WARN`质量，
因此不能产生正式`READY`快照。

## S1：可独立运行骨架完成条件

- 使用Python 3.12和`uv.lock`冻结Qlib、NumPy、PyArrow、LightGBM与Web依赖；Mac和Ubuntu均从锁文件安装。
- `src/quant_research/domain.py`只放领域值对象和确定性计算；`src/quant_research/adapters/qlib.py`是唯一允许出现Qlib专有逻辑的边界，当前不加载真实数据。
- 健康接口保持可运行；`/ready`显式报告当前能力阶段，避免误判为已具备生产因子、回测或快照能力。
- 单元测试必须覆盖稳定Hash、空洞不被填充、UTC与审批字段、以及`WARN`不可升级。真实Qlib、MinIO和PostgreSQL验证留在后续S2及Ubuntu门禁。

Mac的S0/S1回归入口为`./scripts/stage03-verify-mac.sh`；脚本必须从`uv.lock`安装，不得复用其他服务的虚拟环境。

## S2：最小纵向切片完成条件

`QlibCloseGapIndexAdapter`只经`VerifiedArtifactReader`读取对象，先校验原始归档和空洞索引的SHA-256，
再校验索引内`archiveHash`等于父DataVersion原始Artifact Hash。Adapter只解析索引，不读取、转换或写回
Qlib价格。`CloseGapMaskService`输出掩码与`ResearchRunManifest`；北交所标识被排除，所有结果保持`WARN`及
`CANDIDATE_ONLY`。Hash不匹配、缺失对象、无效索引或父归档关系不成立均应失败。

## S3：股票池与Factor Registry基础完成条件

`HistoricalUniverseDefinition`以`asOfDate + cutoffAt`冻结样本；证券状态晚于`cutoffAt`、上市时间不足、
已退市、ST、停牌、流动性不足或北交所证券均不得进入快照。快照成员稳定排序并产生规范内容Hash。

`FactorDefinition`和`FactorVersion`使用`DRAFT / CANDIDATE / ACTIVE / RETIRED`生命周期。价格质量门禁、
估值PIT门禁和财务修订PIT门禁未满足时不得将因子提升为`CANDIDATE`；生产`FactorSet`只接受`ACTIVE`
因子，禁止把`CANDIDATE`直接带入生产。当前仅实现领域规则和Fixture验证，未实现真实因子计算或Registry持久化。

## S4：价格类因子Fixture完成条件

首批`price.momentum.2d`、`price.volatility.2d`和`liquidity.average-turnover.3d`由Qlib Adapter边界内的
Fixture实现产生。输入按`securityId + tradingDay`排序；因子明细按`securityId + tradingDay + factorId`稳定排序，
值量化至8位小数，规范内容Hash不依赖Mac或Ubuntu运行时间。任何停牌掩码日及其三日回看窗口均不产生收益率、
价格或流动性因子。输出继承`WARN`，仅用于开发、研究及候选验证；真实Qlib表达式、数据集与Artifact输出将在后续步骤替换该Fixture Adapter。

## S5：版本化变换Fixture完成条件

`TransformSpec`固定UTC截止时间、MAD去极值倍率、行业中性化、市值中性化和标准化开关。`availableAt`晚于截止
时间、原始因子缺失、行业缺失（启用行业中性化时）或市值缺失（启用市值中性化时）的行必须排除，不能以零、当期值
或未来值替代。输出值统一量化至8位小数、按三字段排序，并保持`WARN`；真实行业分类、市值PIT和Transform Artifact
持久化属于后续Qlib/组件集成步骤。

## S6：Qlib Artifact Adapter完成条件

`QlibDatasetMaterializer`只能经`VerifiedArtifactReader`读取阶段02的`artifactUri + SHA-256`，并把合法的
`qlib_bin/`安全解压到以`dataVersionId / artifactHash`命名的本地只读缓存。归档路径逃逸、符号链接、设备文件、
不含`qlib_bin/`、对象Hash不匹配或缓存标记不匹配均必须失败。只有完成上述检查的Provider目录才可调用
`initialize_qlib_provider`。S3/MinIO访问限制在配置Bucket，服务不读取阶段02数据库、不下载供应商数据，也不把
解压目录复制到Ubuntu；Ubuntu按固定Commit和同一Artifact引用原生重建缓存。

真实本机冒烟使用`./scripts/stage03-qlib-artifact-smoke.py --cache-root <临时目录>`。脚本只能从
`GET /api/v1/data-versions/latest`获得引用，输出DataVersion、两个输入Hash、质量结论和Qlib交易日日历数量；
并随机验证一个非北交所空洞的原始`close=NaN`及`SUSPENSION_ASSUMED`掩码；不得打印MinIO密钥，也不得将缓存提交Git。

真实冒烟还使用同一Provider的`D.features`读取最近30个交易日的`$close`与`$amount`，通过
`QlibMaskedPriceFactorService`生成动量、波动率和流动性因子。输出中只要出现空洞掩码股票日即失败；
因子输出及Run Manifest必须继续为`WARN / CANDIDATE_ONLY`。

## S7：因子矩阵不可变Artifact完成条件

价格因子矩阵先以`securityId + tradingDay + factorId`稳定排序，生成跨平台比较用的
`canonicalContentHash`；再写出Parquet Artifact并记录该文件的SHA-256。矩阵与Run Manifest均使用
内容寻址MinIO键且不可覆盖。Manifest必须引用因子Parquet URI/SHA-256、规范内容Hash、TransformVersion、
父DataVersion、空洞索引和策略Artifact，并保持`WARN / CANDIDATE_ONLY`。Parquet SHA-256允许跨CPU不同，
但规范内容Hash不同必须判定失败。

真实烟测只有附带`--publish-factor-artifacts`才会写入MinIO。该模式先把烟测策略正文写为独立的不可变Policy
Artifact，再写因子Parquet与Run Manifest；相同内容可重复执行，键冲突但内容不同必须失败。烟测审批引用仅限本地
开发验证，不能作为正式`CANDIDATE`或生产审批凭证。

## S7：真实Qlib价格读取完成条件

`QlibPriceFeatureReader`只能在已完成S6初始化的只读Provider上查询`$close`与`$amount`，并转换为领域
`DailyPriceBar`。Qlib的证券代码统一转为小写以与`close-gap-index`一致；`NaN`、非有限、负数或零收盘价必须
保留为缺失而不能删除、填充或跨越。价格因子Adapter对任一三日窗口中的缺失或停牌掩码均不产生输出。真实读取仍
继承DataVersion的`WARN`，不构成正式READY数据或因子集验收。

## S8：价格因子候选准入完成条件

价格动量、波动率与流动性因子从`DRAFT`进入`CANDIDATE`时，必须同时提交该因子所在的已发布矩阵、不可变
Run Manifest Artifact、矩阵规范内容Hash、固定DataVersion、TransformVersion和人工审批引用。门禁逐项校验：
因子必须实际出现在矩阵中；版本、DataVersion与TransformVersion必须与Manifest完全一致；矩阵与规范Hash不得缺失；
输入质量不得为`FAIL`；Manifest仍必须是`CANDIDATE_ONLY`。输出为不可变候选记录，显式标记`RESEARCH_ONLY`，
不能直接构建生产`FactorSet`。

候选证据读取器必须先按Artifact SHA-256读取Manifest和Parquet，而非信任调用方传入的因子列表或Hash；随后校验
Parquet列、行排序、固定8位Decimal、单一DataVersion，并从内容重算`canonicalContentHash`。任何对象Hash、Schema、
数据版本、排序或规范Hash不一致均拒绝准入。

本地烟测使用的`stage03-local-smoke`审批引用只能证明链路可运行，明确禁止作为正式候选审批。默认烟测为只读；
只有`--publish-factor-artifacts`会创建Policy、矩阵和Manifest Artifact。正式候选审批、回测证据与生产激活
将在后续阶段完成。

## 首版数据依赖与准入顺序

真实数据验证使用阶段02发布的固定`investment_data` Release DataVersion，Release Tag、归档/Manifest Hash、质量报告和来源策略版本必须进入Run Manifest。不得由量化服务自行下载或修补原始数据。

1. 先验证价格动量、波动率和流动性因子；它们可在主日频数据通过PIT、复权、停牌和质量门禁后进入`CANDIDATE`。
2. 再验证价值因子；只有历史PE/PB/PS/PCF覆盖率、口径和`availableAt`检查通过，才允许从`DRAFT`提升。
3. 最后验证质量及财务修订类因子；必须具备财务公告时间、原值、修订值、修订原因和原公告Artifact证据。
4. 补充源尚未实现或覆盖不足时，相关因子只做Fixture测试并保持`DRAFT`，不得用当前值回填历史或降低门禁。

具体来源职责和后续实现项见[阶段02首版数据源与PIT补全策略](../02-market-data-service/05-v1-data-source-policy.md)。

```python
class FactorVersion(BaseModel):
    factor_id: str
    version: str
    expression_hash: str
    data_version: str
    transform_version: str
    status: Literal["DRAFT", "CANDIDATE", "ACTIVE", "RETIRED"]
```

## 测试

- 历史股票池不使用未来成分。
- 相同DataVersion和FactorVersion得到相同Hash。
- CANDIDATE不能进入生产FactorSet。
- 停牌、缺失和极端值处理符合版本规则。
- 同一DataVersion、`close-gap-index` Hash和CloseGapHandlingPolicy必须生成相同停牌掩码与`canonicalContentHash`；策略Artifact或索引Hash缺失、变更或不匹配必须失败。
- 收盘空洞在按需解释模式下保持`NaN`，只能被排除出可交易性、收益率和价格因子分母；不得填充、前向填充或伪造BaoStock事实。
- 使用`assume_suspension_on_read`时Run Manifest与快照质量必须为`WARN`，且不得晋级为正式READY快照。
- 未满足估值或财务PIT数据门禁时，价值/质量因子不能进入CANDIDATE或ACTIVE。
- Run Manifest中的Release、输入Hash、来源策略版本与DataVersion一致。
- 价格因子候选必须绑定已发布矩阵和Run Manifest；因子缺席、版本不一致、`FAIL`质量、非`CANDIDATE_ONLY`输出或本地烟测审批均必须拒绝。
- 伪造候选元数据、被篡改Manifest、Parquet的行顺序或规范Hash必须由证据读取器拒绝。
