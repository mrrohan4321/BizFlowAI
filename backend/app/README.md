# backend/app

Request path: **route -> schema (validation) -> service -> database / ai_ml**.

| File / folder | Role |
|---|---|
| `main.py` | creates the FastAPI app, registers routers, CORS, error handlers, `/api/health` |
| `config.py` | reads environment variables. Loads `.env` first, then puts the repo root on `sys.path` so `ai_ml` can be imported |
| `auth.py` | `get_current_user` (verify Supabase JWT) and `get_business_id` (resolve allowed business). Put `Depends(get_business_id)` on every new route |
| `errors.py` | `AppError(status, code, message, details)` and global handlers. Raise `AppError` from services |
| `utils.py` | `serialize(row)` for JSON-friendly rows |
| `db/` | connections, transactions, migrations |
| `routes/` | HTTP layer only |
| `schemas/` | request validation |
| `services/` | business logic and SQL |

Do not import `ai_ml` before `app.config` has been imported (it reads `.env` at import time).
