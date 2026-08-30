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
