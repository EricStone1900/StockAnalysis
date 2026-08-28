# 01-02 标准化、Point-in-Time与数据质量

## 目标

把原始行情和财务披露转换为可回放、带`availableAt`的数据，并在发布前执行质量门禁。

## 实施步骤

### 1. 标准行情模型

```python
class DailyBar(BaseModel):
    symbol: str
    exchange: str
    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    amount: Decimal
    adjustment_factor: Decimal
    source: str
    available_at: datetime
```

价格、金额和复权因子使用Decimal或数据库NUMERIC，不使用二进制浮点作为事实值。

### 2. Point-in-Time查询

```sql
SELECT *
FROM research.financial_fact
WHERE symbol = :symbol
  AND report_period <= :report_period
  AND available_at <= :decision_time
ORDER BY report_period DESC, available_at DESC;
```

历史回测只允许读取`available_at <= decision_time`的数据。修订报表生成新版本，不能覆盖旧值。

### 3. 质量规则接口

```python
class QualityRule(Protocol):
    rule_id: str
    version: str
    def evaluate(self, dataset: DataFrame) -> QualityResult: ...
```

第一版规则：主键重复、未来时间、OHLC关系、负值、交易日缺失、停牌与缺失区分、复权跳变和跨源差异。

### 4. 结果聚合

```python
def publishable(results: list[QualityResult]) -> bool:
    return all(result.status != "FAIL" for result in results)
```

WARN随DataVersion保存；FAIL阻断发布。禁止捕获异常后把FAIL改成WARN。

### 5. 原始与标准数据

- Raw文件不可变写入MinIO。
- 标准记录保存`sourceRecordId`和Raw Artifact URI。
- 数据修复生成新版本，不覆盖已参与历史决策的数据。

## 测试案例

1. 2025年1月决策看不到2025年3月披露数据。
2. 财报修订前后在不同decisionTime返回不同版本。
3. high低于close时质量FAIL。
4. 停牌日不会被误判为行情缺失。
5. WARN版本可发布且查询返回warning摘要。

## 完成条件

- PIT查询有自动测试防止未来数据。
- 每条标准记录可追溯Raw Artifact。
- 质量报告与数据版本绑定。

