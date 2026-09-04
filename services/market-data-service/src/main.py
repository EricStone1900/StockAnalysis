import logging
import os
from datetime import date
from secrets import compare_digest

from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError

from market_data.application import DuplicateSecurityError, MarketDataService
from market_data.baostock_status import BaoStockSdkClient, BaoStockTradingStatusAdapter, RetryPolicy
from market_data.domain import Exchange, Security, SecurityId
from market_data.importing import (
    BaoStockStatusEnrichmentCommand,
    BaoStockStatusImportService,
    InvestmentDataImportCommand,
    InvestmentDataImportService,
)
from market_data.investment_data import InvestmentDataReleaseAdapter
from market_data.nats_publisher import nats_jetstream_publisher
from market_data.prices import PricePoint, VersionedPriceStore
from market_data.publishing import DataVersionPublisher
from market_data.repository import PostgresSourceLineageRepository, PostgresStatusBatchRepository
from market_data.runtime import endpoint_reachable, environment_secret
from market_data.status_enrichment import BaoStockStatusEnrichmentService, StatusEnrichmentResult
from market_data.storage import ArtifactStore
from market_data.versioning import DataVersion
from market_data.worker_executor import MultiprocessingWorkerExecutor

app = FastAPI(title="market-data-service", version="0.1.0")
service = MarketDataService()
price_store = VersionedPriceStore()
logger = logging.getLogger(__name__)


def create_data_version_publisher() -> DataVersionPublisher:
    """从环境变量装配本地或容器环境的 MinIO 与 NATS 适配器。"""
    store = ArtifactStore(
        endpoint_url=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
        access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=environment_secret("MINIO_SECRET_KEY", "local-minio-password"),
        bucket=os.getenv("ARTIFACT_BUCKET", "artifacts"),
    )
    return DataVersionPublisher(service.versions, store, nats_jetstream_publisher(os.getenv("NATS_URL", "nats://localhost:4222")))


data_version_publisher = create_data_version_publisher()
source_lineage_repository = PostgresSourceLineageRepository(
    os.getenv("MARKET_DATA_DATABASE_URL", "postgresql://localhost:5432/market_data")
)


def create_investment_data_import_service() -> InvestmentDataImportService:
    store = data_version_publisher.artifact_store
    return InvestmentDataImportService(
        adapter=InvestmentDataReleaseAdapter(),
        artifact_writer=store,
        lineage=source_lineage_repository,
        publisher=data_version_publisher,
        artifact_uri_prefix=f"minio://{store.bucket}",
    )


investment_data_import_service = create_investment_data_import_service()


def create_baostock_status_import_service() -> BaoStockStatusImportService:
    store = data_version_publisher.artifact_store
    lineage = source_lineage_repository
    enrichment = BaoStockStatusEnrichmentService(
        BaoStockTradingStatusAdapter(
            BaoStockSdkClient,
            retry_policy=RetryPolicy(
                max_attempts=int(os.getenv("BAOSTOCK_MAX_ATTEMPTS", "3")),
                initial_backoff_seconds=float(os.getenv("BAOSTOCK_INITIAL_BACKOFF_SECONDS", "1")),
                min_interval_seconds=float(os.getenv("BAOSTOCK_MIN_INTERVAL_SECONDS", "0.2")),
                query_timeout_seconds=float(os.getenv("BAOSTOCK_QUERY_TIMEOUT_SECONDS", "30")),
            ),
            worker_executor=MultiprocessingWorkerExecutor(
                float(os.getenv("BAOSTOCK_QUERY_TIMEOUT_SECONDS", "30"))
            ),
        ),
        store,
        lineage,
        f"minio://{store.bucket}",
    )
    return BaoStockStatusImportService(
        store,
        store,
        enrichment,
        data_version_publisher,
        f"minio://{store.bucket}",
        PostgresStatusBatchRepository(os.getenv("MARKET_DATA_DATABASE_URL", "postgresql://localhost:5432/market_data")),
    )


baostock_status_import_service = create_baostock_status_import_service()


class RegisterSecurityRequest(BaseModel):
    exchange: Exchange
    symbol: str
    name: str


class PublishDataVersionRequest(BaseModel):
    version: DataVersion


class ImportInvestmentDataRequest(InvestmentDataImportCommand):
    pass


class ImportBaoStockStatusRequest(BaoStockStatusEnrichmentCommand):
    pass


def require_import_token(import_token: str) -> None:
    expected_token = environment_secret("MARKET_DATA_IMPORT_TOKEN", "")
    if not expected_token:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="import task is not enabled")
    if not compare_digest(import_token, expected_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid import token")


async def parse_internal_request(request: Request, model: type[BaseModel]) -> BaseModel:
    try:
        body = await request.json()
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid JSON body") from error
    try:
        return model.model_validate(body)
    except ValidationError as error:
        raise RequestValidationError(error.errors()) from error


@app.get("/live")
def live() -> dict[str, str]:
    return {"status": "UP"}

@app.get("/ready")
def ready(response: Response) -> dict[str, object]:
    dependencies = {
        "postgres": endpoint_reachable(os.getenv("MARKET_DATA_DATABASE_URL", "postgresql://localhost:5432/market_data")),
        "minio": endpoint_reachable(os.getenv("MINIO_ENDPOINT", "http://localhost:9000")),
        "nats": endpoint_reachable(os.getenv("NATS_URL", "nats://localhost:4222")),
    }
    is_ready = all(dependencies.values())
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "UP" if is_ready else "DOWN", "dependencies": dependencies}

@app.get("/metrics")
def metrics() -> str:
    return ""

@app.get("/version")
def version() -> dict[str, str]:
    return {"service": "market-data-service", "version": "0.1.0"}

@app.post("/api/v1/securities", status_code=status.HTTP_201_CREATED)
def register_security(request: RegisterSecurityRequest, idempotency_key: str = Header(alias="Idempotency-Key")) -> Security:
    try:
        security = Security(security_id=SecurityId(exchange=request.exchange, symbol=request.symbol), name=request.name)
        return service.register_security(security, idempotency_key)
    except DuplicateSecurityError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="security already exists") from error

@app.get("/api/v1/securities/{symbol}")
def get_security(symbol: str) -> Security:
    security = service.get_security(symbol)
    if security is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="security not found")
    return security

@app.get("/api/v1/securities/{symbol}/status")
def get_status(symbol: str) -> dict[str, str]:
    return {"status": get_security(symbol).status}


@app.get("/api/v1/prices/{symbol}", response_model=PricePoint)
def get_price(symbol: str, dataVersion: str, asOf: date) -> PricePoint:
    price = price_store.get(symbol, dataVersion, asOf)
    if price is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="price not found for data version and date")
    return price

@app.get("/api/v1/calendars/{market}")
def calendar(market: str, day: date) -> dict[str, object]:
    if market != "CN_A":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="market not found")
    return {"market": market, "day": day, "isTradingDay": service.calendar.is_trading_day(day), "sessions": service.calendar.sessions(day)}


@app.get("/api/v1/data-versions/latest")
def latest_data_version() -> DataVersion:
    latest = service.versions.latest_ready() or source_lineage_repository.latest_ready_data_version()
    if latest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no ready data version")
    return latest


@app.post("/api/v1/data-versions", status_code=status.HTTP_201_CREATED)
async def publish_data_version(
    request: PublishDataVersionRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> DataVersion:
    try:
        return await data_version_publisher.publish(request.version, idempotency_key)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@app.post("/internal/v1/jobs/import-investment-data", status_code=status.HTTP_201_CREATED)
async def import_investment_data(
    raw_request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    import_token: str = Header(alias="X-Import-Token"),
) -> DataVersion:
    require_import_token(import_token)
    request = await parse_internal_request(raw_request, ImportInvestmentDataRequest)
    assert isinstance(request, ImportInvestmentDataRequest)
    try:
        return await investment_data_import_service.import_release(request, idempotency_key)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@app.post("/internal/v1/jobs/enrich-baostock-status", status_code=status.HTTP_201_CREATED)
async def enrich_baostock_status(
    raw_request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    import_token: str = Header(alias="X-Import-Token"),
) -> DataVersion | StatusEnrichmentResult:
    require_import_token(import_token)
    request = await parse_internal_request(raw_request, ImportBaoStockStatusRequest)
    assert isinstance(request, ImportBaoStockStatusRequest)
    try:
        return await baostock_status_import_service.import_status(request, idempotency_key)
    except (RuntimeError, ValueError) as error:
        logger.warning("baostock status enrichment rejected: %s", error)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
