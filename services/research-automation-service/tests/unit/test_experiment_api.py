from fastapi.testclient import TestClient

from src.main import app


def test_create_and_read_experiment() -> None:
    client = TestClient(app)
    payload = {
        "experiment_id": "api-experiment-1",
        "hypothesis": "固定实验",
        "data_version_id": "dv-1",
        "data_artifact_uri": "minio://market-data/dv-1.tar.gz",
        "data_artifact_hash": "c" * 64,
        "script_id": "fixed-factor-smoke-v1",
        "random_seed": 1,
    }
    created = client.post("/internal/v1/experiments", headers={"Idempotency-Key": "api-key-1"}, json=payload)
    assert created.status_code == 201
    assert created.json()["status"] == "QUEUED"
    repeated = client.post("/internal/v1/experiments", headers={"Idempotency-Key": "api-key-1"}, json=payload)
    assert repeated.status_code == 201
    assert repeated.json()["created"] is False
    assert client.get("/internal/v1/experiments/api-experiment-1").status_code == 200


def test_experiment_api_rejects_unknown_script_and_unknown_experiment() -> None:
    client = TestClient(app)
    response = client.post(
        "/internal/v1/experiments",
        headers={"Idempotency-Key": "api-key-2"},
        json={
            "experiment_id": "api-experiment-2",
            "hypothesis": "固定实验",
            "data_version_id": "dv-1",
            "data_artifact_uri": "minio://market-data/dv-1.tar.gz",
            "data_artifact_hash": "d" * 64,
            "script_id": "untrusted-script",
            "random_seed": 1,
        },
    )
    assert response.status_code == 409
    assert client.get("/internal/v1/experiments/missing").status_code == 404
