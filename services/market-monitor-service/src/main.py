from datetime import datetime
from typing import Any, cast

from fastapi import FastAPI, HTTPException

from src.monitoring import (
    AnomalyDeduplicator,
    ClosedBar,
    Quote,
    RuleVersion,
    Watchlist,
    aggregate_closed_bars,
    detect_anomaly,
)

app = FastAPI(title="market-monitor-service", version="0.1.0")
deduplicator = AnomalyDeduplicator()


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


@app.post("/internal/v1/anomalies/evaluate")
def evaluate_anomaly(payload: dict[str, object]) -> dict[str, object]:
    try:
        previous = ClosedBar.model_validate(payload["previous"])
        current = ClosedBar.model_validate(payload["current"])
        rule = RuleVersion.model_validate(payload["rule"])
        event = detect_anomaly(previous, current, rule, float(str(payload["baselineVolume"])))
        if event is None:
            return {"published": False, "reason": "NO_ANOMALY_OR_BAD_QUALITY"}
        if not deduplicator.accept(event):
            return {"published": False, "reason": "DUPLICATE", "eventId": event.event_id}
        return {"published": True, "event": event}
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
