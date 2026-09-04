from src.monitoring import SnapshotQuality


def test_snapshot_quality_fails_closed_for_provider_or_coverage() -> None:
    assert SnapshotQuality(source="free", schema_version="v1", quote_age_seconds=1, coverage=1, provider_available=True).gate() == "PASS"
    assert SnapshotQuality(source="free", schema_version="v1", quote_age_seconds=181, coverage=1, provider_available=True).gate() == "STALE"
    assert SnapshotQuality(source="free", schema_version="v1", quote_age_seconds=1, coverage=0.9, provider_available=True).gate() == "FAIL"
    assert SnapshotQuality(source="free", schema_version="v1", quote_age_seconds=1, coverage=1, provider_available=False).gate() == "FAIL"
