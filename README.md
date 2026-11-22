# BizFlow AI

AI-powered finance assistant for small businesses. **Team Finnovate - Arthaton 2026.**

Upload an invoice, let OCR + AI read it, review and confirm it, then track payments, expenses, overdue invoices,
monthly performance and a cash-flow estimate, and ask questions about your money in plain language.

**Core principle:** AI helps with *understanding* (OCR, field extraction, explaining answers).
**Python does every financial calculation.** The LLM never does arithmetic and never writes SQL.

Repository: https://github.com/mrrohan4321/BizFlowAI
Live API (Swagger): https://bizflow-backend-2onh.onrender.com/docs

---

## 1. Team

| # | Member | Role | Owns |
|---|---|---|---|
| 1 | **Ronit Jana** | Frontend | `frontend/` |
| 2 | **Rohan Adak** | Backend | `backend/`, `database/`, `render.yaml` (API, database, deployment) |
| 3 | **Rajdeep Panja** | AI / ML | `ai_ml/` (OCR, extraction, validation, metrics, forecasting, assistant) |

`sample_data/` and `API-notes.md` are shared. If you change something in a folder, update that folder's README in the same commit.

## 2. Project status

| Area | Folder | Status | Details |
|---|---|---|---|
| AI/ML module (OCR, extraction, validation, metrics, forecast, assistant) | `ai_ml/` | Done, unit-tested | [ai_ml/README.md](ai_ml/README.md) |
| Backend API (FastAPI + Postgres + Supabase auth) | `backend/` | Done, tested, deployed on Render | [backend/README.md](backend/README.md) |
| Database (schema, migrations, RLS, demo seed) | `database/` | Done | [database/README.md](database/README.md) |
| Frontend (React) | `frontend/` | Implemented (8 screens); live end-to-end check with real login still to be ticked off | [frontend/README.md](frontend/README.md) |
| Sample data (synthetic invoices) | `sample_data/` | Done | [sample_data/README.md](sample_data/README.md) |
| Architecture diagram / screenshots / demo video | - | See section 11 | - |

## 3. What the product does

```
Upload invoice -> OCR + AI extraction -> human review/edit -> confirm & save
   -> dashboard (receivables, payables, overdue, monthly) -> record payments / expenses
   -> opening cash -> cash-flow forecast -> grounded finance assistant (chat)
```

Rules the whole team keeps:

1. **Nothing AI-extracted is saved without the user pressing confirm** (`confirmed: true`).
2. **Receivables** = outstanding *sales* invoices. **Payables** = outstanding *purchase* invoices. Never added together.
3. **Cash** = actual payments only. Unpaid invoices and unpaid expenses are never cash.
4. A cost is recorded as a purchase invoice **or** an expense, never both (double counting).
5. The business is resolved **on the server** from the logged-in user. The frontend never sends a `business_id`.
6. The forecast needs an **opening cash balance** (month-end date). Without it the API answers `409 opening_cash_required`. Zero is never assumed.
7. Forecast and `operating_surplus_estimate` are **estimates**, always labelled as such.

## 4. Architecture

```
 Browser (React, Vercel)                       Supabase
 ┌──────────────────────┐   login (email+pw)  ┌───────────────┐
 │ frontend/            │ ──────────────────► │ Auth          │
 │ Vite + React + TW    │ ◄── access_token ── │               │
 └──────────┬───────────┘                     │ PostgreSQL    │
            │ HTTPS + Bearer token            │ (RLS on)      │
            ▼                                 └───────▲───────┘
 ┌──────────────────────┐   SQL (psycopg2)            │
 │ backend/  FastAPI    │ ────────────────────────────┘
 │ auth, isolation,     │
 │ uploads, endpoints   │──► ai_ml/  OCR, extraction, validation,
 └──────────────────────┘            metrics, forecast, assistant ──► Groq LLM
        (Render)
```

- Supabase is used by the browser **only for login**. All business data goes through the FastAPI backend.
- The backend sends only the logged-in business's records to `ai_ml` (and therefore to Groq).

## 5. Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 7, Tailwind CSS 4, React Router 7, Recharts 3, Axios, lucide-react, Supabase JS (login only) |
| Backend | FastAPI, Pydantic v2, psycopg2 (raw SQL, no ORM), PyJWT |
| Database / Auth | Supabase PostgreSQL + Supabase Auth, Row Level Security |
| AI/ML | RapidOCR + PyMuPDF (OCR), Groq LLM (`openai/gpt-oss-120b`), Decimal-based Python finance maths, moving-average forecast |
| Hosting | Render (backend, `render.yaml`), Vercel/Netlify-style static hosting for the frontend (`frontend/vercel.json`) |

## 6. Repository structure

```
BizFlowAI/
├── README.md              <- you are here
├── API-notes.md           shared API contract (endpoint table + money rules)
├── .env.example           names of backend environment variables (no secrets)
├── render.yaml            Render deployment blueprint for the backend
├── backend/               FastAPI app, tests, smoke test             -> backend/README.md
│   ├── app/               main, auth, config, errors, routes/, services/, schemas/, db/
│   ├── tests/             pytest suite (needs a Postgres URL)        -> backend/tests/README.md
│   └── scripts/           smoke_test.py (checks a running server)    -> backend/scripts/README.md
├── ai_ml/                 AI/ML module                               -> ai_ml/README.md
│   ├── BACKEND_CLAUDE_HANDOFF.md   brief used to build the backend around this module
│   └── tests/             pytest suite (no DB, Groq is mocked)       -> ai_ml/tests/README.md
├── database/              schema.sql, migrations/, seed_demo.sql     -> database/README.md
├── frontend/              React app                                  -> frontend/README.md
│   ├── FRONTEND_CLAUDE_HANDOFF.md  brief used to build the frontend
│   └── src/               pages/, components/, services/
└── sample_data/           synthetic invoices only                    -> sample_data/README.md
```

## 7. Quick start (local)

Requirements: Python 3.12, Node.js 20.19+ (or 22.12+), a Supabase project (free tier is fine), a Groq API key (only for extraction and the assistant).

```bash
# 1. backend
cd backend && python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env     # fill DATABASE_URL, SUPABASE_URL (+ SUPABASE_JWT_SECRET for HS256 projects), GROQ_API_KEY
python -m app.db.migrate       # creates tables (schema.sql + migrations)
uvicorn app.main:app --reload  # API docs: http://localhost:8000/docs

# 2. demo data (optional): edit demo_user in database/seed_demo.sql, then run it in the Supabase SQL Editor

# 3. frontend
cd frontend && npm install
cp .env.example .env           # VITE_API_URL, VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY
npm run dev                    # http://localhost:5173
```

> The backend `.env` lives in the **repo root**, not in `backend/`. `backend/app/config.py` loads it before `ai_ml` is imported.
> The frontend has its own `frontend/.env` (public values only).
> You can skip step 1 and point the frontend at the deployed backend: `VITE_API_URL=https://bizflow-backend-2onh.onrender.com`.

### Getting a token for Swagger (/docs -> Authorize)

Create a user in Supabase (Authentication -> Users), then:

```bash
curl -X POST "$SUPABASE_URL/auth/v1/token?grant_type=password" -H "apikey: <anon key>" \
  -H "Content-Type: application/json" -d '{"email":"you@example.com","password":"..."}'
```

Paste the `access_token` into **Authorize**. A new user also needs a row in `business_members`
(the demo seed creates it) - otherwise every endpoint returns `403 no_business_access`.

## 8. Demo script (5 minutes)

Uses the seeded business "Sen Electricals" (see [database/README.md](database/README.md)):

1. Log in. Overview shows receivables **45,000** and payables **20,000**, and the overdue invoice list.
2. Upload `sample_data/invoices/sales_INV-103_total_mismatch.png`: the review screen shows a validation **warning**; nothing is saved yet.
3. Upload `sales_INV-102_clean.png`, fix a field, press **Confirm & save**. (INV-102 already exists in the seed, so change the number or expect `409 duplicate_invoice`.)
4. Open INV-102 and record a **10,000 payment**: receivables drop to **35,000**.
5. Cash flow: opening cash 150,000 (2026-10-31) is already seeded; open the forecast and read its assumptions and disclaimer.
6. Assistant: "How much do my customers owe me?", "Which invoices are overdue?", "What is my expected cash flow?".

## 9. Tests

```bash
# backend (runs inside a throw-away Postgres schema; real data is never touched)
cd backend && TEST_DATABASE_URL=postgresql://... python -m pytest tests -v
# ai_ml (from the repo root; no DB and no API key needed, Groq is mocked)
python -m pytest ai_ml/tests -v
# frontend
cd frontend && npm run build
```

Re-run them before every merge. Details: [backend/tests/README.md](backend/tests/README.md), [ai_ml/tests/README.md](ai_ml/tests/README.md).
The frontend has no automated tests yet; `npm run build` must pass and the demo script above is the manual check.

## 10. Environment variables, deployment, privacy

- **Backend:** see [.env.example](.env.example) and [backend/README.md](backend/README.md#environment-variables).
  Needed: `DATABASE_URL`, `SUPABASE_URL` (+ `SUPABASE_JWT_SECRET` for legacy HS256 projects), `GROQ_API_KEY`,
  `ALLOWED_ORIGINS` (must contain the frontend URL, otherwise the browser blocks every call with a CORS error).
- **Frontend:** `VITE_API_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` ([frontend/README.md](frontend/README.md)). Public values only.
- Never commit `.env` files, the database password, the JWT secret or the Groq key.
- **Backend deployment:** Render, via [render.yaml](render.yaml) (free plan, Singapore). Live API: https://bizflow-backend-2onh.onrender.com (health: `/api/health`).
  The start command runs migrations, then uvicorn. Free plan: the service sleeps after inactivity (first request can take about a minute) and has 512 MB RAM.
  Verify a deployment with `python backend/scripts/smoke_test.py`.
- **Frontend deployment:** static hosting (Vercel config included). After deploying, add the frontend's HTTPS URL to `ALLOWED_ORIGINS` on Render.
- **Privacy:** invoice text is sent to **Groq** (a third-party AI service) for field extraction, and assistant questions plus the
  calculated result are sent to Groq to write the answer. Use synthetic data for demos. Never commit real invoices
  (`sample_data/real/` and `uploads/` are git-ignored).

## 11. Working agreement and remaining TODO

- `API-notes.md` is the shared contract. **Agree before changing an endpoint**, then update `API-notes.md`, `backend/README.md`,
  the frontend service layer and the tests together.
- Do not move financial calculations into the frontend or the LLM prompts. They belong to `ai_ml/`.
- Only synthetic data goes in `sample_data/`.

Remaining before/after submission:

- [ ] Run the demo script above once against the deployed backend with the real demo login (ticks off the frontend end-to-end check).
- [ ] Add screenshots of the main screens (Overview, Upload review, Cash flow, Assistant) to this README.
- [ ] Record the demo video / prepare the pitch.
- [ ] Ideas for later: signup / "create my business" endpoint, invoice file download, expense-specific assistant tool, frontend tests.
