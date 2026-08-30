from market_data.status_batches import StatusBatch, StatusBatchState


def test_status_batch_contract_exposes_immutable_identity_fields() -> None:
    batch = StatusBatch(
        batch_id="a" * 64,
        ordinal=0,
        gap_count=50,
        first_key="SSE:600000:2000-01-01",
        last_key="SSE:600001:2000-01-02",
    )

    assert batch.state is StatusBatchState.PENDING
    assert batch.model_dump(include={"batch_id", "ordinal", "gap_count", "first_key", "last_key"}) == {
        "batch_id": "a" * 64,
        "ordinal": 0,
        "gap_count": 50,
        "first_key": "SSE:600000:2000-01-01",
        "last_key": "SSE:600001:2000-01-02",
    }
