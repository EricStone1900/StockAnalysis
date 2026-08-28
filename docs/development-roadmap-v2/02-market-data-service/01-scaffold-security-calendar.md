# 02-01 骨架、Security与Calendar

## 实施步骤

1. 从Python服务模板创建`market-data-service`，配置独立数据库和MinIO Bucket。
2. 建立`Security`、`Exchange`、`TradingCalendar`、`TradingSession`和值对象`SecurityId`。
3. 实现证券注册、代码映射、状态更新和指定日期交易时段查询。
4. 先实现CSV/Fixture Adapter，再接第一个真实数据源；Adapter输出统一Raw DTO。
5. 写入Security/Calendar时同事务保存Outbox事件。

领域骨架：

```python
class SecurityId(BaseModel):
    market: Literal["CN_A"]
    exchange: Literal["SSE", "SZSE", "BSE"]
    symbol: str

class TradingCalendarPort(Protocol):
    def is_trading_day(self, day: date) -> bool: ...
    def sessions(self, day: date) -> list[TradingSession]: ...
```

## 测试

- 代码映射、退市、停牌状态和重复注册。
- 周末、节假日、午间休市和时区边界。
- 同一Idempotency-Key重复导入只产生一个版本。
- Domain不依赖供应商SDK。

## 完成条件

Security和Calendar API、迁移、事件与Fixture闭环独立通过。

