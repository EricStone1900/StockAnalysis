# 03-01 Qlib、股票池与Factor Registry

## 实施步骤

1. 从Python模板建立服务，Adapter只读取market-data发布的不可变DataVersion Artifact。
2. 建立历史股票池快照，纳入上市天数、ST、停牌、流动性和退市样本规则。
3. 建立FactorDefinition、FactorVersion、FactorSet Aggregate和DRAFT/CANDIDATE/ACTIVE状态。
4. 首批实现价格动量、波动率、流动性、价值和质量基础因子。
5. 统一缺失值、去极值、标准化和行业/市值中性化版本。
6. Qlib表达式封装在Adapter，不泄漏到Domain和跨服务DTO。

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

