# BizFlow AI

AI-powered finance assistant for small businesses. Team Finnovate - Arthaton 2026.

**Core principle:** AI helps with *understanding* (OCR, field extraction, explaining answers). **Python does every
financial calculation.** The LLM never does arithmetic and never writes SQL.

---

## 1. Project status (read this first)

| Area | Folder | Status | Details |
|---|---|---|---|
| AI/ML (OCR, extraction, validation, metrics, forecast, assistant) | `ai_ml/` | Done, tested | [ai_ml/README.md](ai_ml/README.md) |
| Backend API (FastAPI + Postgres + Supabase auth) | `backend/` | Done, tested, deployed on Render | [backend/README.md](backend/README.md) |
| Database (schema, migrations, demo seed) | `database/` | Done | [database/README.md](database/README.md) |
| Sample data (synthetic invoices) | `sample_data/` | Done | [sample_data/README.md](sample_data/README.md) |
| **Frontend (React)** | `frontend/` | **NOT STARTED - only an empty skeleton** | [frontend/README.md](frontend/README.md) |
| Architecture diagram / screenshots / demo video | - | TODO | section 9 |

**Whoever builds the frontend: start with [frontend/README.md](frontend/README.md) and
[frontend/FRONTEND_CLAUDE_HANDOFF.md](frontend/FRONTEND_CLAUDE_HANDOFF.md).** The backend is finished; you only consume its API.

## 2. What the product does

```
Upload invoice -> OCR + AI extraction -> human review/edit -> confirm & save
   -> dashboard (receivables, payables, overdue, monthly) -> record payments / expenses
   -> opening cash -> cash-flow forecast -> grounded finance assistant (chat)
```

Key rules the whole team must keep:

1. **Nothing AI-extracted is saved without the user pressing confirm** (`confirmed: true`).
2. **Receivables** = outstanding *sales* invoices. **Payables** = outstanding *purchase* invoices. Never added together.
3. **Cash** = actual payments only. Unpaid invoices / unpaid expenses are never cash.
4. A cost is recorded as a purchase invoice **or** an expense - not both (double counting).
5. The business is resolved **on the server** from the logged-in user. The frontend never sends a `business_id`.
6. Forecast needs an **opening cash balance** (month-end date). Without it the API answers `409 opening_cash_required`.

## 3. Stack

React + Vite + Tailwind (frontend, planned) | FastAPI + Pydantic + psycopg2 (backend) | Supabase PostgreSQL + Supabase Auth |
RapidOCR + PyMuPDF (OCR) | Groq LLM (`openai/gpt-oss-120b`) | Decimal-based Python finance maths | Render (hosting)

## 4. Repository structure

```
BizFlowAI/
├── README.md              <- you are here
├── API-notes.md           shared API contract (endpoints table + money rules)
├── .env.example           names of all environment variables (no secrets)
├── render.yaml            Render deployment blueprint for the backend
├── backend/               FastAPI app, tests, smoke-test script      -> backend/README.md
│   ├── app/               main.py, auth.py, config.py, errors.py, routes/, services/, schemas/, db/
│   ├── tests/             pytest suite (needs a Postgres URL)        -> backend/tests/README.md
│   └── scripts/           smoke_test.py (checks a running server)    -> backend/scripts/README.md
├── ai_ml/                 OCR, extraction, validation, metrics, forecast, assistant
│   ├── README.md          module documentation
│   ├── BACKEND_CLAUDE_HANDOFF.md   the brief that was used to build the backend around this module
│   └── tests/             pytest suite (no DB, Groq is mocked)
├── database/              schema.sql, migrations/, seed_demo.sql     -> database/README.md
├── frontend/              React app (to be built)                    -> frontend/README.md
└── sample_data/           synthetic invoices only                    -> sample_data/README.md
```

## 5. Quick start (local)

Requirements: Python 3.12, Node 18+ (for the frontend later), a Supabase project (free tier is fine).

```bash
# 1. backend
cd backend && python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env          # fill DATABASE_URL, SUPABASE_URL (+ SUPABASE_JWT_SECRET for HS256 projects), GROQ_API_KEY
python -m app.db.migrate            # creates tables (schema.sql + migrations)
uvicorn app.main:app --reload       # API docs: http://localhost:8000/docs

# 2. demo data (optional): edit demo_user in database/seed_demo.sql, then run it in the Supabase SQL Editor

# 3. frontend (after it is created - see frontend/README.md)
cd frontend && npm install && npm run dev      # http://localhost:5173
```

> `.env` lives in the **repo root** (not in `backend/`). `backend/app/config.py` loads it before `ai_ml` is imported.

### Getting a token for Swagger (/docs -> Authorize)

Create a user in Supabase (Authentication -> Users), then:

```bash
curl -X POST "$SUPABASE_URL/auth/v1/token?grant_type=password" -H "apikey: <anon key>" \
  -H "Content-Type: application/json" -d '{"email":"you@example.com","password":"..."}'
```

Paste the `access_token` into **Authorize**. A new user also needs a row in `business_members`
(the demo seed creates it for you) - otherwise every endpoint returns `403 no_business_access`.

## 6. Tests

```bash
# backend (runs inside a throw-away Postgres schema; real data is never touched)
cd backend && TEST_DATABASE_URL=postgresql://... python -m pytest tests -v
# ai_ml (from the repo root; no DB and no API key needed - Groq is mocked)
python -m pytest ai_ml/tests -v
```

Re-run both suites before every merge. Test descriptions: [backend/tests/README.md](backend/tests/README.md).

## 7. Environment variables

See [.env.example](.env.example). Required to run the backend: `DATABASE_URL`, `SUPABASE_URL`
(+ `SUPABASE_JWT_SECRET` only for legacy HS256 projects), `GROQ_API_KEY` (only for extraction + assistant),
`ALLOWED_ORIGINS` (must contain the frontend URL, otherwise the browser blocks every call with a CORS error).
Never commit `.env`.

## 8. Deployment

Backend is deployed on Render using [render.yaml](render.yaml) (free plan, Singapore).

- **Live API / Swagger:** https://bizflow-backend-2onh.onrender.com/docs
- Health: https://bizflow-backend-2onh.onrender.com/api/health
- Frontend developers can use this URL as `VITE_API_URL` without running the backend locally. The start command runs
migrations automatically, then starts uvicorn. Health check: `GET /api/health`.
After deploying, run `python backend/scripts/smoke_test.py` to verify everything end to end.
Details: [backend/README.md](backend/README.md#deployment-render).

Free-plan notes: the service sleeps after inactivity (first request can take ~1 minute) and has 512 MB RAM
(OCR can run out of memory on very large images).

## 9. Working agreement for the team

- `API-notes.md` is the shared contract. **Agree before changing an endpoint**, then update `API-notes.md`,
  `backend/README.md` and the frontend service layer together.
- Never commit real invoices or secrets. Only synthetic data goes in `sample_data/`.
- Each folder has its own README. If you change something in a folder, update that folder's README in the same commit.
- Do not move financial calculations into the frontend or the LLM prompts - they belong to `ai_ml/`.

### Remaining TODO
- [ ] Build the frontend (`frontend/`).
- [ ] Add architecture diagram and screenshots to this README.
- [ ] Add team members and roles below.
- [ ] Record demo video / prepare pitch.

## 10. Team

TODO: list members and roles (AI/ML, Backend + Database + Deployment, Frontend, ...).
