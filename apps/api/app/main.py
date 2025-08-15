from fastapi import FastAPI
from .settings import settings

app = FastAPI(title="DataWoven API")

@app.get("/health")
def health():
    return {"ok": True, "env": settings.environment}
