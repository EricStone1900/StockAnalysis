import hashlib
import io
import math
import struct
import tarfile

import pytest

from market_data.qlib_quality import (
    QlibQualityReason,
    build_close_gap_index,
    close_gap_index_bytes,
    extract_qlib_close_gaps,
    parse_close_gap_index,
    validate_qlib_daily_archive,
)
from market_data.quality import QualityStatus


def archive_with_features(*, include_close: bool = True, invalid_ohlc: bool = False, close_gap: bool = False) -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        files = {
            "qlib_bin/calendars/day.txt": b"2026-08-27\n2026-08-28\n",
            "qlib_bin/instruments/all.txt": b"sh600000\t2020-01-01\t2026-08-28\n",
        }
        values = {
            "open": (10.0, 11.0),
            "high": (11.0, 12.0),
            "low": (9.0, 10.0),
            "close": (10.5, math.nan if close_gap else 11.5),
            "volume": (100.0, 120.0),
        }
        if invalid_ohlc:
            values["high"] = (9.0, 12.0)
        for field, series in values.items():
            if field == "close" and not include_close:
                continue
            files[f"qlib_bin/features/sh600000/{field}.day.bin"] = struct.pack("<3f", 0.0, *series)
        for name, content in files.items():
            entry = tarfile.TarInfo(name)
            entry.size = len(content)
            archive.addfile(entry, io.BytesIO(content))
    return stream.getvalue()


def test_daily_quality_accepts_complete_ohlcv_archive() -> None:
    report = validate_qlib_daily_archive(archive_with_features())
    assert report.status is QualityStatus.PASS
    assert report.close_feature_coverage == 1.0


def test_daily_quality_fails_missing_close_or_invalid_ohlc() -> None:
    missing = validate_qlib_daily_archive(archive_with_features(include_close=False))
    invalid = validate_qlib_daily_archive(archive_with_features(invalid_ohlc=True))
    assert missing.status is QualityStatus.FAIL
    assert QlibQualityReason.MISSING_FEATURE in missing.reasons
    assert invalid.status is QualityStatus.FAIL
    assert QlibQualityReason.INVALID_OHLC in invalid.reasons


def test_daily_quality_warns_when_close_gap_has_no_trading_status_evidence() -> None:
    report = validate_qlib_daily_archive(archive_with_features(close_gap=True))
    assert report.status is QualityStatus.WARN
    assert QlibQualityReason.UNCLASSIFIED_CLOSE_GAP in report.reasons


def test_extract_close_gaps_keeps_security_and_calendar_coordinates() -> None:
    gaps = extract_qlib_close_gaps(archive_with_features(close_gap=True))
    assert [(gap.symbol, gap.trading_day.isoformat()) for gap in gaps] == [("sh600000", "2026-08-28")]


def test_close_gap_index_is_bound_to_the_parent_archive() -> None:
    archive = archive_with_features(close_gap=True)
    archive_hash = hashlib.sha256(archive).hexdigest()
    index = build_close_gap_index(archive, archive_hash)

    restored = parse_close_gap_index(close_gap_index_bytes(index), archive_hash)
    assert restored == index
    with pytest.raises(ValueError, match="parent archive"):
        parse_close_gap_index(close_gap_index_bytes(index), "a" * 64)
