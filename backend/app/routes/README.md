# routes/

Thin FastAPI routers. They declare the URL, parameters and the auth dependency, then call a function in
`services/`. No SQL and no money maths here.

| File | Endpoints |
|---|---|
| `invoices.py` | `POST /api/invoices/extract`, `POST /api/invoices`, `GET /api/invoices`, `GET/PATCH/PUT/DELETE /api/invoices/{id}` |
| `finance.py` | `/api/payments`, `/api/expenses`, `/api/expenses/{id}`, `/api/opening-cash` |
| `analytics.py` | `/api/analytics/summary`, `/api/analytics/monthly`, `/api/analytics/overdue` (+ `/api/payments/overdue`), `/api/forecast` |
| `assistant.py` | `POST /api/assistant/chat` |

Rules: every route (except `/api/health` in `main.py`) uses `Depends(get_business_id)`; list endpoints use
`limit` (1 to 500, default 100) and `offset`; path ids are typed `UUID`, so a malformed id returns 422.
