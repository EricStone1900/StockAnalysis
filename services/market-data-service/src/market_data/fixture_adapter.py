import csv
from collections.abc import Iterator
from pathlib import Path

from .domain import Exchange, Security, SecurityId


def load_securities(path: Path) -> Iterator[Security]:
    with path.open(newline="", encoding="utf-8") as source:
        for row in csv.DictReader(source):
            if not row.get("exchange") or not row.get("symbol") or not row.get("name"):
                raise ValueError("supplier fixture missing required security field")
            yield Security(security_id=SecurityId(exchange=Exchange(row["exchange"]), symbol=row["symbol"]), name=row["name"])
