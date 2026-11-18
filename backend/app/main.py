from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import ALLOWED_ORIGINS
from app.db.database import get_cursor

app = FastAPI(title="BizFlow AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    try:
        with get_cursor() as cur:
            cur.execute("SELECT 1 AS ok")
            db_ok = cur.fetchone()["ok"] == 1
    except Exception:
        db_ok = False
    return {"status": "ok", "database": db_ok}
