import io
import math
import struct
import tarfile
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from pydantic import BaseModel

from .quality import QualityStatus

REQUIRED_PRICE_FIELDS = ("open", "high", "low", "close", "volume")


class QlibQualityReason(StrEnum):
    MISSING_FEATURE = "missing_feature"
    INVALID_FEATURE_SERIES = "invalid_feature_series"
    INVALID_PRICE = "invalid_price"
    INVALID_OHLC = "invalid_ohlc"
    UNCLASSIFIED_CLOSE_GAP = "unclassified_close_gap"
    OHLC_ALIGNMENT_UNVERIFIED = "ohlc_alignment_unverified"


class QlibDailyQualityReport(BaseModel):
    status: QualityStatus
    reasons: tuple[QlibQualityReason, ...]
    trading_day_count: int
    instrument_count: int
    close_feature_coverage: float
    nonfinite_close_count: int


class QlibCloseGap(BaseModel):
    symbol: str
    trading_day: date


class QlibCloseGapIndex(BaseModel):
    """不可变空洞索引；将昂贵的归档遍历从批次执行路径移出。"""

    archive_hash: str
    gaps: tuple[QlibCloseGap, ...]


def build_close_gap_index(archive_bytes: bytes, archive_hash: str) -> QlibCloseGapIndex:
    return QlibCloseGapIndex(archive_hash=archive_hash, gaps=extract_qlib_close_gaps(archive_bytes))


def close_gap_index_bytes(index: QlibCloseGapIndex) -> bytes:
    return index.model_dump_json(exclude_none=True).encode()


def parse_close_gap_index(content: bytes, archive_hash: str) -> QlibCloseGapIndex:
    index = QlibCloseGapIndex.model_validate_json(content)
    if index.archive_hash != archive_hash:
        raise ValueError("close gap index does not belong to parent archive")
    return index


@dataclass(frozen=True)
class _FeatureStats:
    start_index: int
    value_count: int
    nonfinite_count: int
    minimum: float | None
    maximum: float | None
    sample: tuple[float, ...]


def validate_qlib_daily_archive(archive_bytes: bytes) -> QlibDailyQualityReport:
    """检查Qlib日频输入本身的范围、字段覆盖与可识别价格异常。"""
    try:
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
            members = {member.name: member for member in archive.getmembers() if member.isfile()}
            calendar = _read_text_lines(archive, members.get("qlib_bin/calendars/day.txt"))
            instruments = _read_text_lines(archive, members.get("qlib_bin/instruments/all.txt"))
            feature_stats = _read_feature_stats(archive, members, instruments)
    except (OSError, tarfile.TarError, EOFError) as error:
        raise ValueError("unable to inspect qlib daily archive") from error

    reasons: set[QlibQualityReason] = set()
    if not calendar or not instruments:
        reasons.add(QlibQualityReason.INVALID_FEATURE_SERIES)
    symbols = _instrument_symbols(instruments)
    if len(symbols) != len(instruments):
        reasons.add(QlibQualityReason.INVALID_FEATURE_SERIES)
    missing_close = 0
    nonfinite_close_count = 0
    for symbol in symbols:
        fields = feature_stats.get(symbol, {})
        for field in REQUIRED_PRICE_FIELDS:
            if field not in fields:
                reasons.add(QlibQualityReason.MISSING_FEATURE)
        if any(
            stats.start_index < 0 or stats.start_index + stats.value_count > len(calendar)
            for stats in fields.values()
        ):
            reasons.add(QlibQualityReason.INVALID_FEATURE_SERIES)
        close = fields.get("close")
        if close is None:
            missing_close += 1
            continue
        nonfinite_close_count += close.nonfinite_count
        if close.minimum is None or close.minimum <= 0:
            reasons.add(QlibQualityReason.INVALID_PRICE)
        for field in ("open", "high", "low"):
            stats = fields.get(field)
            if stats is not None and (stats.minimum is None or stats.minimum <= 0):
                reasons.add(QlibQualityReason.INVALID_PRICE)
        _validate_ohlc_sample(fields, reasons)

    if nonfinite_close_count:
        reasons.add(QlibQualityReason.UNCLASSIFIED_CLOSE_GAP)
    coverage = 0.0 if not symbols else (len(symbols) - missing_close) / len(symbols)
    status = _quality_status(reasons)
    return QlibDailyQualityReport(
        status=status,
        reasons=tuple(sorted(reasons)),
        trading_day_count=len(calendar),
        instrument_count=len(symbols),
        close_feature_coverage=coverage,
        nonfinite_close_count=nonfinite_close_count,
    )


def extract_qlib_close_gaps(archive_bytes: bytes) -> tuple[QlibCloseGap, ...]:
    """从原始Qlib二进制直接枚举收盘空洞，不修改任何行情值。"""
    try:
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
            members = {member.name: member for member in archive.getmembers() if member.isfile()}
            calendar = [date.fromisoformat(day) for day in _read_text_lines(archive, members.get("qlib_bin/calendars/day.txt"))]
            symbols = _instrument_symbols(_read_text_lines(archive, members.get("qlib_bin/instruments/all.txt")))
            gaps: list[QlibCloseGap] = []
            for symbol in symbols:
                member = members.get(f"qlib_bin/features/{symbol}/close.day.bin")
                if member is None:
                    continue
                stats, values = _feature_values(archive, member)
                for offset, value in enumerate(values):
                    index = stats.start_index + offset
                    if not math.isfinite(value) and 0 <= index < len(calendar):
                        gaps.append(QlibCloseGap(symbol=symbol, trading_day=calendar[index]))
    except (OSError, tarfile.TarError, EOFError, ValueError) as error:
        raise ValueError("unable to extract qlib close gaps") from error
    return tuple(gaps)


def _read_text_lines(archive: tarfile.TarFile, member: tarfile.TarInfo | None) -> list[str]:
    if member is None:
        return []
    content = archive.extractfile(member)
    if content is None:
        return []
    return [line for line in content.read().decode("utf-8").splitlines() if line]


def _read_feature_stats(
    archive: tarfile.TarFile, members: dict[str, tarfile.TarInfo], instruments: list[str]
) -> dict[str, dict[str, _FeatureStats]]:
    result: dict[str, dict[str, _FeatureStats]] = {}
    for row in instruments:
        parts = row.split("\t")
        if len(parts) != 3 or not parts[0]:
            continue
        symbol = parts[0].lower()
        prefix = f"qlib_bin/features/{symbol}/"
        result[symbol] = {}
        for name, member in members.items():
            if not name.startswith(prefix) or not name.endswith(".day.bin"):
                continue
            field = name.removeprefix(prefix).removesuffix(".day.bin")
            result[symbol][field] = _feature_stats(archive, member)
    return result


def _instrument_symbols(instruments: list[str]) -> list[str]:
    symbols: list[str] = []
    for row in instruments:
        parts = row.split("\t")
        if len(parts) == 3 and parts[0]:
            symbols.append(parts[0].lower())
    return symbols


def _feature_stats(archive: tarfile.TarFile, member: tarfile.TarInfo) -> _FeatureStats:
    stats, _ = _feature_values(archive, member)
    return stats


def _feature_values(archive: tarfile.TarFile, member: tarfile.TarInfo) -> tuple[_FeatureStats, tuple[float, ...]]:
    content = archive.extractfile(member)
    if content is None:
        raise ValueError("feature member is unreadable")
    raw = content.read()
    if len(raw) < 8 or len(raw) % 4:
        raise ValueError("feature series is malformed")
    values = struct.unpack(f"<{len(raw) // 4}f", raw)
    start_index = int(values[0])
    if values[0] != start_index:
        raise ValueError("feature start index is malformed")
    finite = [value for value in values[1:] if math.isfinite(value)]
    return _FeatureStats(
        start_index=start_index,
        value_count=len(values) - 1,
        nonfinite_count=len(values) - 1 - len(finite),
        minimum=min(finite) if finite else None,
        maximum=max(finite) if finite else None,
        sample=tuple(values[1:33]),
    ), tuple(values[1:])


def _validate_ohlc_sample(fields: dict[str, _FeatureStats], reasons: set[QlibQualityReason]) -> None:
    selected = {field: fields.get(field) for field in ("open", "high", "low", "close")}
    if any(stats is None for stats in selected.values()):
        return
    stats = tuple(selected.values())
    if len({item.start_index for item in stats if item is not None}) != 1:
        reasons.add(QlibQualityReason.OHLC_ALIGNMENT_UNVERIFIED)
        return
    if len({len(item.sample) for item in stats if item is not None}) != 1:
        reasons.add(QlibQualityReason.OHLC_ALIGNMENT_UNVERIFIED)
        return
    for open_, high, low, close in zip(*(item.sample for item in stats if item is not None), strict=True):
        if all(math.isfinite(value) for value in (open_, high, low, close)) and not (
            low <= min(open_, close) <= max(open_, close) <= high
        ):
            reasons.add(QlibQualityReason.INVALID_OHLC)


def _quality_status(reasons: set[QlibQualityReason]) -> QualityStatus:
    failures = {
        QlibQualityReason.MISSING_FEATURE,
        QlibQualityReason.INVALID_FEATURE_SERIES,
        QlibQualityReason.INVALID_PRICE,
        QlibQualityReason.INVALID_OHLC,
    }
    if reasons & failures:
        return QualityStatus.FAIL
    if reasons:
        return QualityStatus.WARN
    return QualityStatus.PASS
