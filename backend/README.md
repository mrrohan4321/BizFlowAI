# Backend (FastAPI)

REST API that sits between the frontend and the `ai_ml/` module. It owns authentication, business isolation,
database access, file uploads and every endpoint. It does **not** contain financial formulas - receivables,
payables, overdue, summary and forecast numbers all come from `ai_ml/`.

Interactive docs when running: **http://localhost:8000/docs** (Swagger). Shared contract: [../API-notes.md](../API-notes.md).

## 1. What was built

| Feature | Where |
|---|---|
| Supabase JWT auth (HS256 secret, or ES256/RS256 via JWKS) | `app/auth.py` |
| Business isolation (resolved from `business_members`, never from the request) | `app/auth.py` -> `get_business_id` |
| Invoice upload -> OCR/AI extraction -> staging (nothing saved) | `app/services/invoices.py`, `uploads.py` |
| Explicit confirm/save, list, get, update, delete invoices | `app/services/invoices.py` |
| Payments (partial / multiple, overpayment blocked, row-locked) | `app/services/payments.py` |
| Expenses with `paid`/`unpaid` (cash vs recognised cost) | `app/services/expenses.py` |
| Opening cash balance (month-end, never assumed 0) | `app/services/cash.py` |
| Summary, monthly, overdue, forecast | `app/services/analytics.py` |
| Finance assistant chat | `app/services/assistant.py` |
| Uniform error format, no stack traces leaked | `app/errors.py` |
| Migration runner | `app/db/migrate.py` |
| Safe uploads (extension + magic bytes + size, server-generated names) | `app/services/uploads.py` |
| Tests, smoke test, Render deployment | `tests/`, `scripts/smoke_test.py`, `../render.yaml` |

## 2. Layout

```
backend/
├── requirements.txt          includes ../ai_ml/requirements.txt + fastapi, uvicorn, psycopg2, pyjwt, pytest, httpx
├── app/
│   ├── main.py               FastAPI app, CORS, routers, GET /api/health
│   ├── config.py             loads ../.env FIRST, puts repo root on sys.path so `import ai_ml` works
│   ├── auth.py               get_current_user (JWT) + get_business_id (membership check)
│   ├── errors.py             AppError + handlers -> {"error": {"code","message","details"}}
│   ├── utils.py              serialize(): Decimal -> number, UUID -> str
│   ├── db/
│   │   ├── database.py       psycopg2 helpers: get_connection() (one transaction), get_cursor()
│   │   └── migrate.py        python -m app.db.migrate
│   ├── routes/               thin HTTP layer (finance.py, invoices.py, analytics.py, assistant.py)
│   ├── schemas/              Pydantic request models (extra fields are FORBIDDEN)
│   └── services/             all logic + SQL (one file per feature)
├── scripts/smoke_test.py     manual end-to-end check of a running server
└── tests/                    pytest suite
```

Design choices: plain **psycopg2 + raw SQL** (no ORM); routes are thin; every query has `WHERE business_id = %s`;
the app imports `ai_ml` lazily for the assistant so startup does not depend on the Groq SDK.

## 3. Run locally

```bash
cd backend
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env                                # then fill it (repo ROOT, not backend/)
python -m app.db.migrate                                  # prints: applied: [...] or "nothing (up to date)"
uvicorn app.main:app --reload                             # http://localhost:8000/docs
```

Check: `GET /api/health` -> `{"status":"ok","database":true}`.
Run all backend commands **from `backend/`** (imports are `app.*`).

### Environment variables

| Variable | Needed for | Notes |
|---|---|---|
| `DATABASE_URL` | everything | Supabase Postgres connection string (use the pooler string on Render) |
| `SUPABASE_URL` | auth (ES256/RS256) | e.g. `https://xxxx.supabase.co`; JWKS is fetched from it |
| `SUPABASE_JWT_SECRET` | auth (HS256 only) | legacy Supabase projects only |
| `JWT_AUDIENCE` | auth | default `authenticated` |
| `GROQ_API_KEY` | extraction + assistant | tests do not need it (mocked). Missing key -> `503 ai_not_configured` |
| `ALLOWED_ORIGINS` | CORS | comma separated; must include the frontend URL |
| `UPLOAD_DIR` | uploads | default `<repo>/uploads` (Render: `/tmp/uploads`, ephemeral) |
| `MAX_UPLOAD_MB` | uploads | default 10 |
| `EXTRACTION_TTL_MINUTES` | review window | default 60 |
| `TEST_DATABASE_URL` | tests only | Postgres URL tests may create a temp schema in |
| `DB_SCHEMA` | tests only | **never set in production** |

`SUPABASE_KEY` and `DEMO_BUSINESS_ID` in `.env.example` are not read by the backend code today.

## 4. Authentication and business isolation

1. Frontend logs in with Supabase Auth and gets an `access_token`.
2. Every request except `/api/health` sends `Authorization: Bearer <access_token>`.
3. The backend verifies the JWT and reads `sub` (user id).
4. It looks the user up in `business_members` -> that is the business. **There is no `business_id` in any request body**
   (schemas use `extra="forbid"`, so sending one gives 422).
5. If the user belongs to several businesses, send header `X-Business-Id: <uuid>` to *select* one of them.

| Situation | Status / code |
|---|---|
| No / bad / expired token | 401 `unauthenticated` |
| User has no business | 403 `no_business_access` |
| `X-Business-Id` not theirs | 403 `forbidden_business` |
| Several businesses and no header | 400 `business_required` |

> A new Supabase user can log in but gets 403 until a row exists in `business_members`.
> There is **no signup/onboarding endpoint yet** (see Known limitations). For now insert the row by SQL
> (`database/seed_demo.sql` does it for the demo user).

## 5. Endpoints

All paths are prefixed with `/api`. Errors always look like `{"error": {"code", "message", "details?"}}`.

### Invoices

| Method | Path | Notes |
|---|---|---|
| POST | `/invoices/extract` | multipart field **`file`** (PDF/JPG/PNG, max 10 MB). Returns extraction for review. **Saves nothing.** |
| POST | `/invoices` | Save after review. Body needs `"confirmed": true`; `extraction_id` optional (omit for manual entry). 201 |
| GET | `/invoices` | filters: `invoice_type`, `status`, `date_from`, `date_to`, `party`, `limit` (<=500), `offset`. Returns `{items, total}` |
| GET | `/invoices/{id}` | detail with `amount_paid`, `outstanding_amount`, `status` |
| PATCH or PUT | `/invoices/{id}` | partial update (re-validated) |
| DELETE | `/invoices/{id}` | 204. Blocked (409) if payments exist |

Extract response:
```json
{ "extraction_id": "uuid", "extraction_status": "ok | ai_extraction_failed",
  "extracted_fields": { "invoice_number": "INV-102", "invoice_type": "sales", "party_name": "...", "invoice_date": "2026-10-26",
                        "due_date": "2026-11-10", "subtotal": 25423.73, "tax_amount": 4576.27, "cgst": null, "sgst": null,
                        "igst": null, "total_amount": 30000.0, "gstin": null },
  "warnings": [ { "field": "total_amount", "severity": "warning", "message": "..." } ],
  "needs_review": true, "raw_text_preview": "...", "expires_at": "ISO time", "saved": false }
```
If the LLM failed, `extraction_status = "ai_extraction_failed"`, all fields are null and the user must type the data manually.
An extraction is **single-use** and **expires** (default 60 min): confirm with it twice -> 409 `extraction_already_used`,
too late -> 410 `extraction_expired`.

Confirm: validation *errors* block saving (422 `invalid_invoice`, details list); *warnings* still save, with
`review_status = "needs_review"`. Duplicate (same business + type + number) -> 409 `duplicate_invoice`.

### Payments

| Method | Path | Notes |
|---|---|---|
| POST | `/payments` | `{invoice_id, amount, payment_date, method?, reference?, note?}`. Returns `{payment, invoice}` with the new balance/status. Overpayment -> 422 `overpayment` |
| GET | `/payments` | filters `invoice_id`, `date_from`, `date_to`, `limit`, `offset` -> `{items}` |
| GET | `/payments/overdue` | alias of `/analytics/overdue` |

### Expenses and opening cash

| Method | Path | Notes |
|---|---|---|
| POST | `/expenses` | `{category, amount, expense_date, description?, notes?, payment_status: unpaid|paid, paid_date?}` - `paid` requires `paid_date`, `unpaid` forbids it |
| GET | `/expenses` | filters `category`, `payment_status`, `date_from`, `date_to`, `limit`, `offset` -> `{items}` |
| PATCH | `/expenses/{id}` | e.g. mark paid: `{"payment_status":"paid","paid_date":"2026-11-12"}` |
| PUT | `/opening-cash` | `{amount, as_of_date, note?}`; `as_of_date` **must be a month-end**; one row per date (upsert); amount may be negative |
| GET | `/opening-cash` | `{items}` newest first |

### Analytics, forecast, assistant

| Method | Path | Returns |
|---|---|---|
| GET | `/analytics/summary` (`date_from`, `date_to`) | `sales_total, expense_total, receivables, payables, operating_surplus_estimate, currency, notes` |
| GET | `/analytics/monthly` | `labels[]`, `sales[]`, `expenses[]` (recorded) and `cash_income[]`, `cash_outflows[]` (actual), `cash_summary` - arrays are aligned to `labels` (chart-ready) |
| GET | `/analytics/overdue` (`as_of`) | `count`, `overdue_receivables_total`, `overdue_payables_total`, `invoices[]` (each has `direction`: receivable/payable, `days_overdue`) |
| GET | `/forecast` (`months` 1-12 default 3, `window` 1-12 default 3) | `periods[]`, `values[]` ({predicted_income, predicted_outflows, predicted_closing_cash}), `method`, `assumptions[]`, `warnings[]`, `insufficient_data`, `opening_cash`, `closing_cash`, `disclaimer`. **409 `opening_cash_required`** until opening cash is set |
| POST | `/assistant/chat` | `{question}` (<=500 chars) -> `{question, answer, tool_used, data_used, insufficient_data, follow_up}` |
| GET | `/health` | `{status, database}` (no auth) |

Note: the route default `window=3` differs from the `ai_ml` default (12). It was chosen so a business with only a few
months of data still gets a forecast; the API reports a warning when fewer months than `window` exist.

## 6. How money is calculated (important)

- The backend loads the business's rows and calls `ai_ml.finance_metrics` / `ai_ml.forecasting` /
  `ai_ml.assistant_tools`. **Do not re-implement these formulas in routes or the frontend.**
- Invoice `amount_paid`, `outstanding_amount`, `status` (`unpaid|partially_paid|paid`) come from `ai_ml.finance_metrics`.
- Cash history for forecast/monthly = payments on **sales** invoices (income) + payments on **purchase** invoices +
  expenses with `payment_status='paid'` (outflows, dated by `paid_date`). Months with no movement count as 0.
- Forecast starts the month **after** the opening-cash `as_of_date`; later payments are excluded from history.
- `operating_surplus_estimate` = recorded sales - recorded expenses. It is **not** cash or profit; the UI must label it that way.

## 7. Error codes the frontend should handle

| HTTP | code | Meaning / suggested UI |
|---|---|---|
| 401 | `unauthenticated` | send user to login / refresh token |
| 403 | `no_business_access`, `forbidden_business` | "no business linked to your account" |
| 400 | `business_required`, `invalid_business_id` | send/choose `X-Business-Id` |
| 404 | `invoice_not_found`, `expense_not_found`, `extraction_not_found` | not found |
| 409 | `duplicate_invoice` | number already exists |
| 409 | `extraction_already_used` | already saved |
| 409 | `invoice_has_payments` | cannot delete |
| 409 | `opening_cash_required` | show "set opening cash" form |
| 410 | `extraction_expired` | ask to upload again |
| 413 | `file_too_large` | max 10 MB |
| 415 | `unsupported_file_type` | PDF/JPG/PNG only |
| 422 | `invalid_request` | field errors in `details[]` (`{field, message}`) |
| 422 | `invalid_invoice` | validation errors in `details[]` |
| 422 | `confirmation_required`, `overpayment`, `total_below_payments`, `ocr_failed`, `empty_file`, `opening_cash_not_month_end` | show `message` |
| 502 | `assistant_failed` | "try again" |
| 503 | `ai_not_configured`, `ocr_unavailable` | AI/OCR temporarily unavailable |
| 500 | `database_error`, `internal_error`, `auth_misconfigured` | generic error |

## 8. Tests

```bash
cd backend
TEST_DATABASE_URL=postgresql://user:pass@host:5432/db python -m pytest tests -v
```
Each run creates a random schema `bf_test_xxxx`, runs the migrations in it and drops it at the end. Groq is mocked; no API key
is needed. Without a Postgres URL the whole backend suite is **skipped** (not failed). See [tests/README.md](tests/README.md).

Also run the AI/ML tests from the repo root: `python -m pytest ai_ml/tests -v`.

## 9. Deployment (Render)

**Live:** [https://bizflow-backend-2onh.onrender.com](https://bizflow-backend-2onh.onrender.com/docs) - Swagger at `/docs`, health at `/api/health`. Frontend uses this as `VITE_API_URL`.

- Blueprint: `../render.yaml` (web service, Python 3.12.7, free plan, Singapore).
- Build: `pip install -r backend/requirements.txt`. Start: `cd backend && python -m app.db.migrate && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- Set these in the Render dashboard (they are `sync: false`): `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_JWT_SECRET` (if HS256),
  `GROQ_API_KEY`, `ALLOWED_ORIGINS` (add the deployed frontend URL!).
- Uploaded files go to `/tmp/uploads` and vanish on restart. That is acceptable because a file is only needed during review.
- Verify: `python backend/scripts/smoke_test.py` (see [scripts/README.md](scripts/README.md)).

## 10. Security checklist (already implemented)

- JWT verified on every route except `/api/health`; business resolved server-side; every SQL filtered by `business_id`.
- Request models reject unknown fields (`extra="forbid"`), so `business_id` cannot be injected.
- Uploads: allowed extensions + magic-byte check + size limit + server-generated filename + path-traversal guard; files cleaned up on failure/expiry.
- Errors never leak SQL, stack traces or API keys; logs contain exception *types* only.
- Row Level Security enabled on every table (`database/migrations/002_enable_rls.sql`) so the public Supabase anon key cannot read data directly.
- Row locks on payments and invoice edits prevent overpayment races.

## 11. Known limitations / ideas for later

- No signup / "create my business" endpoint: a new user needs a `business_members` row inserted by SQL.
- No endpoints for `customers` / `suppliers` tables (they exist in the DB, invoices just store `party_name`) or the `forecasts` table.
- No delete for payments/expenses, no pagination total on payments/expenses.
- Assistant has five tools only (receivables, payables, overdue, monthly performance, cash forecast); it cannot answer expense-specific questions.
- Uploaded invoice files are not downloadable (`has_file` flag only) and are lost on Render restart.
- Single currency per business (`businesses.currency`, default INR); no multi-currency.
- Render free plan: cold start ~1 min, 512 MB RAM.

## 12. Where to change things

| I want to... | Edit |
|---|---|
| add an endpoint | `routes/<area>.py` + `schemas/<area>.py` + `services/<area>.py`, then a test, then `../API-notes.md` and this README |
| change a table | new file `../database/migrations/00N_*.sql` (never edit applied migrations) |
| change a money formula | `../ai_ml/` (+ its tests), not here |
| allow a new frontend URL | `ALLOWED_ORIGINS` env var |
