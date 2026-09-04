from datetime import datetime
from typing import Any, cast

from fastapi import FastAPI, HTTPException

from src.monitoring import Quote, Watchlist, aggregate_closed_bars

app = FastAPI(title="market-monitor-service", version="0.1.0")


@app.get("/live")
def live() -> dict[str, str]:
    return {"status": "UP"}


@app.post("/internal/v1/bars/aggregate")
def aggregate(payload: dict[str, object]) -> dict[str, object]:
    try:
        watchlist = Watchlist.model_validate(payload["watchlist"])
        watchlist.validate_capacity()
        raw_quotes = cast(list[Any], payload.get("quotes", []))
        quotes = [Quote.model_validate(value) for value in raw_quotes]
        bars = aggregate_closed_bars(quotes, datetime.fromisoformat(str(payload["now"])))
        allowed = {entry.security_id for entry in watchlist.entries}
        return {"bars": [bar for bar in bars if bar.security_id in allowed], "watchlistVersion": watchlist.version}
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
