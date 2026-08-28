from fastapi import FastAPI

app = FastAPI(title="research-automation-service", version="0.1.0")

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
