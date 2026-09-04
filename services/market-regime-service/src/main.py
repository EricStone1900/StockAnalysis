from fastapi import FastAPI, HTTPException

from src.regime import FeatureInput, RegimeDefinition, classify

app = FastAPI(title="market-regime-service", version="0.1.0")


@app.get("/live")
def live() -> dict[str, str]:
    return {"status": "UP"}


@app.post("/internal/v1/regime/classify")
def classify_regime(payload: dict[str, object]) -> dict[str, object]:
    try:
        features = FeatureInput.model_validate(payload["features"])
        definition = RegimeDefinition.model_validate(payload["definition"])
        return {"snapshot": classify(features, definition)}
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
