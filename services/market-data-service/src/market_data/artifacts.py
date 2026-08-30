from hashlib import sha256
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from .pit import DailyBar


def write_qlib_view(bars: list[DailyBar], target: Path) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    table = pa.table({"security_id": [f"{bar.security_id.exchange}:{bar.security_id.symbol}" for bar in bars], "date": [bar.trading_day.isoformat() for bar in bars], "close": [str(bar.close) for bar in bars], "data_version": [bar.artifact.content_hash for bar in bars]})
    pq.write_table(table, target, compression="zstd")
    return sha256(target.read_bytes()).hexdigest()
