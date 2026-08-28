# 02-01 Qlib数据集、股票池和Factor Registry

## 目标

把指定DataVersion转换为Qlib Dataset，保存历史股票池，并实现可版本化因子注册表。

## 实施步骤

### 1. Qlib Adapter

```python
class QlibDataAdapter:
    def prepare(self, data_version: str) -> QlibDatasetRef:
        manifest = self.manifest_repo.require_ready(data_version)
        self.verify_hashes(manifest)
        return self.converter.build(manifest)
```

Adapter必须显式接收DataVersion，禁止默认读取随时间变化的本地Qlib目录。

### 2. 股票池快照

```python
class UniverseSnapshot(BaseModel):
    universe_version: str
    as_of_date: date
    symbols: list[SecurityId]
    inclusion_rules_version: str
    excluded: list[UniverseExclusion]
```

过滤ST、停牌、上市天数、流动性等规则必须版本化。历史回测使用当时股票池，不能使用今天的成分列表。

### 3. Factor Registry

```python
class FactorDefinition(BaseModel):
    factor_id: str
    version: str
    expression: str
    direction: Literal[-1, 1]
    lookback: int
    required_fields: list[str]
    status: Literal["DRAFT", "CANDIDATE", "APPROVED", "ACTIVE", "DEPRECATED"]
```

先实现少量可解释基线因子，例如动量、反转、波动率、成交量和估值。第一版重点是流水线正确，不追求因子数量。

### 4. 因子计算记录

每次运行记录：dataVersion、universeVersion、factorVersion、codeCommit、参数、开始/结束时间和Artifact Hash。

## 测试案例

1. 同一DataVersion和配置产生相同Dataset Hash。
2. 退市股票不会从历史股票池消失。
3. 因子缺少requiredField时任务在计算前失败。
4. DRAFT因子不能被生产任务加载。
5. 因子计算不读取asOfDate之后的数据。

## 完成条件

- Qlib Adapter不泄漏Qlib内部文件格式给API调用方。
- 股票池和因子均有不可变版本。
- 至少两个基线因子端到端计算成功。

