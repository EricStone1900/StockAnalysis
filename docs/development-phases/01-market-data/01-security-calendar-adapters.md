# 01-01 Security Master、交易日历与Provider

## 目标

建立统一证券标识、交易状态、交易日历和可替换数据Provider边界。

## 实施步骤

### 1. 建立领域模型

```python
class Security(BaseModel):
    symbol: str
    exchange: Literal["SSE", "SZSE", "BSE"]
    name: str
    list_date: date
    delist_date: date | None = None
    industry_code: str | None = None
    status: Literal["ACTIVE", "SUSPENDED", "DELISTED"]
    valid_from: datetime
    valid_to: datetime | None = None
```

简称、曾用名和行业变化不能覆盖历史记录，应使用有效期或独立历史表。

### 2. Provider端口

```python
class MarketDataProvider(Protocol):
    async def list_securities(self, as_of: date) -> list[RawSecurity]: ...
    async def get_daily_bars(self, symbols: list[str], start: date, end: date) -> list[RawBar]: ...
    async def get_financial_disclosures(self, symbols: list[str], since: datetime) -> list[RawDisclosure]: ...
```

业务层只接收内部Raw DTO，第三方SDK类型不得越过Provider目录。

### 3. 交易日历

表至少包含`market/date/isTradingDay/openAt/lunchStart/lunchEnd/closeAt/version`。

```python
def is_trading_minute(ts: datetime, session: TradingSession) -> bool:
    local = ts.astimezone(ZoneInfo("Asia/Shanghai"))
    return (
        session.open_at <= local < session.lunch_start
        or session.lunch_end <= local < session.close_at
    )
```

不要用`weekday()`代替正式交易日历。

### 4. 数据库约束

```sql
CREATE UNIQUE INDEX uq_security_version
ON research.security(symbol, exchange, valid_from);

CREATE UNIQUE INDEX uq_trading_calendar
ON research.trading_calendar(market, trade_date, version);
```

### 5. 同步任务

同步任务接收`runId/dataSource/asOf/idempotencyKey`，先写Raw Landing，再标准化。任务重复提交必须返回原runId或安全重跑。

## 测试案例

1. 沪深相同数字代码不会冲突。
2. 曾用名在历史日期能正确解析。
3. 节假日、临时休市和午休判断正确。
4. Provider字段缺失时返回DATA_QUALITY错误。
5. 重复同步不产生重复证券版本。

## 完成条件

- Security Master和Calendar有查询API。
- 至少实现一个主Provider和一个可替换Fake Provider。
- 第三方类型没有出现在领域模块和API契约中。

