"""阶段06三服务契约冒烟：仅使用固定 Fixture，不访问外部服务。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "services/news-intelligence-service"))
from src.news_events import SecurityEntity, build_candidate
from src.news_ingestion import EvidenceArtifact, NewsItem

sys.path.insert(0, str(ROOT / "services/market-monitor-service"))
sys.modules.pop("src", None)
from src.monitoring import ClosedBar, RuleVersion, detect_anomaly

sys.path.insert(0, str(ROOT / "services/market-regime-service"))
sys.modules.pop("src", None)
from src.regime import (
    FeatureInput,
    RegimeDefinition,
    RegimeDimensions,
    classify,
)


def main() -> None:
    item = NewsItem(news_id="smoke-news", source_id="fixture", canonical_url="https://example.test/news", title="星河科技公告", language="zh-CN", published_at="2026-09-04T01:00:00Z", collected_at="2026-09-04T01:01:00Z", available_at="2026-09-04T01:01:00Z", source_reliability=1, content_hash="a" * 64, evidence=EvidenceArtifact(uri="s3://artifacts/news/a.txt", content_hash="a" * 64, license_policy_id="v1"))
    candidate = build_candidate(item, (SecurityEntity(symbol="SSE:1", name="星河科技"),))
    assert candidate.candidate_symbols[0].symbol == "SSE:1"
    previous = ClosedBar(security_id="SSE:1", window_start="2026-09-04T01:30:00Z", window_end="2026-09-04T01:35:00Z", open=100, high=100, low=100, close=100, volume=10, amount=1000, quality="PASS", source_event_ids=["p"])
    current = ClosedBar(security_id="SSE:1", window_start="2026-09-04T01:35:00Z", window_end="2026-09-04T01:40:00Z", open=110, high=110, low=110, close=110, volume=30, amount=3300, quality="PASS", source_event_ids=["c"])
    assert detect_anomaly(previous, current, RuleVersion(version="r1", price_jump_pct=0.05, volume_multiplier=2), 10) is not None
    snapshot = classify(FeatureInput(as_of="2026-09-04T00:00:00Z", dimensions=RegimeDimensions(trend=0.2, breadth=0.5, volatility=0.2, liquidity=0.5), data_version="d1", feature_version="f1", quality="PASS", evidence_ids=("e1",)), RegimeDefinition(version="regime-v1"))
    assert snapshot.data_version == "d1" and snapshot.evidence_ids == ("e1",)
    print("stage06 contract smoke: PASS")


if __name__ == "__main__":
    main()
