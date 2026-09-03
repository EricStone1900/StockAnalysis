import os

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from src.research_automation.application import ExperimentService, InMemoryExperimentRepository
from src.research_automation.domain import DEFAULT_SANDBOX_BUDGET, ExperimentInput, SandboxBudget
from src.research_automation.persistence import PostgresExperimentRepository
from src.research_automation.sandbox import FixedScriptSandbox

app = FastAPI(title="research-automation-service", version="0.1.0")
_database_url = os.getenv("RESEARCH_AUTOMATION_DATABASE_URL")
_repository = InMemoryExperimentRepository() if not _database_url else PostgresExperimentRepository(_database_url)
_experiments = ExperimentService(_repository, FixedScriptSandbox())


class SandboxBudgetRequest(BaseModel):
    cpu_limit: float = Field(default=DEFAULT_SANDBOX_BUDGET.cpu_limit, gt=0)
    memory_mb: int = Field(default=DEFAULT_SANDBOX_BUDGET.memory_mb, gt=0)
    disk_mb: int = Field(default=DEFAULT_SANDBOX_BUDGET.disk_mb, gt=0)
    pid_limit: int = Field(default=DEFAULT_SANDBOX_BUDGET.pid_limit, gt=0)
    timeout_seconds: int = Field(default=DEFAULT_SANDBOX_BUDGET.timeout_seconds, gt=0)
    log_limit_bytes: int = Field(default=DEFAULT_SANDBOX_BUDGET.log_limit_bytes, gt=0)


class CreateExperimentRequest(BaseModel):
    experiment_id: str = Field(min_length=1)
    hypothesis: str = Field(min_length=1)
    data_version_id: str = Field(min_length=1)
    data_artifact_uri: str = Field(min_length=1)
    data_artifact_hash: str = Field(min_length=64, max_length=64)
    script_id: str = Field(min_length=1)
    parameters: dict[str, str] = Field(default_factory=dict)
    random_seed: int
    budget: SandboxBudgetRequest = Field(default_factory=SandboxBudgetRequest)


def _experiment_payload(experiment_id: str) -> dict[str, object]:
    experiment = _experiments.get(experiment_id)
    if experiment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="experiment not found")
    run = experiment.run
    return {
        "experimentId": experiment.experiment_id,
        "status": experiment.status,
        "inputHash": experiment.input_hash,
        "dataVersionId": experiment.input.data_version_id,
        "scriptId": experiment.input.script_id,
        "run": None if run is None else {
            "runId": run.run_id,
            "status": run.status,
            "sandboxConfigHash": run.sandbox_config_hash,
            "exitCode": run.exit_code,
        },
    }

@app.get("/live")
def live() -> dict[str, str]:
    return {"status": "UP"}

@app.get("/ready")
def ready() -> dict[str, object]:
    return {"status": "UP", "dependencies": {}}

@app.get("/metrics")
def metrics() -> str:
    return ""

@app.get("/version")
def version() -> dict[str, str]:
    return {"service": "research-automation-service", "version": "0.1.0"}


@app.post("/internal/v1/experiments", status_code=status.HTTP_201_CREATED)
def create_experiment(
    request: CreateExperimentRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> dict[str, object]:
    budget = SandboxBudget(**request.budget.model_dump())
    input_value = ExperimentInput(
        hypothesis=request.hypothesis,
        data_version_id=request.data_version_id,
        data_artifact_uri=request.data_artifact_uri,
        data_artifact_hash=request.data_artifact_hash,
        script_id=request.script_id,
        parameters=request.parameters,
        random_seed=request.random_seed,
        budget=budget,
    )
    try:
        submitted = _experiments.submit(request.experiment_id, idempotency_key, input_value)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    response = _experiment_payload(submitted.experiment.experiment_id)
    response["created"] = submitted.created
    return response


@app.get("/internal/v1/experiments/{experiment_id}")
def get_experiment(experiment_id: str) -> dict[str, object]:
    return _experiment_payload(experiment_id)
