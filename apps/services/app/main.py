from fastapi import FastAPI
from .settings import settings

app = FastAPI(title="DataWoven API")

@app.get("/health")
def health():
    return {"ok": True, "env": settings.environment}

@app.post("/ask")
def ask(q: str, kb_id: str, user=Depends(auth)):
    result = bus.handle(c.AskQuestion(kb_id=kb_id, query=q, user_id=user.id))
    return result
