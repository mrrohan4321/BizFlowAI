from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import ALLOWED_ORIGINS
from app.db.database import get_cursor
from app.errors import register_error_handlers
from app.routes import analytics, assistant, finance, invoices

app = FastAPI(title="BizFlow AI")
register_error_handlers(app)
app.include_router(finance.router)
app.include_router(invoices.router)
app.include_router(analytics.router)
app.include_router(assistant.router)

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
