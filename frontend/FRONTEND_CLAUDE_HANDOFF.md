# BizFlowAI — Frontend Implementation Handoff

> How to use: open the repository in Claude (or another coding assistant) and paste this whole file as the first message.
> Same idea as `ai_ml/BACKEND_CLAUDE_HANDOFF.md`, which was used to build the backend.

## YOUR ROLE

You are the lead frontend engineer for **BizFlowAI**, an AI-powered finance assistant for small businesses (Indian SMEs, INR).
Build the complete React frontend in `frontend/`. The backend, database and AI/ML module are **finished, tested and deployed**.
Do not merely plan: create the files, run the build, and verify against the real API.

---

# 1. FIRST: INSPECT THE REPOSITORY

Before writing code, read:

1. `README.md` (root) — product flow and the key money rules.
2. `backend/README.md` — **the complete API reference** (endpoints, bodies, responses, error codes).
3. `API-notes.md` — shared contract and money rules.
4. `frontend/README.md` — screens, structure, definition of done (this is your spec; follow it).
5. `sample_data/README.md` and `database/README.md` — demo data and known answers.
6. Optionally `backend/app/routes/*.py` and `backend/app/schemas/*.py` for exact field names and validation limits.

`frontend/` currently has only empty `src/components`, `src/pages`, `src/services` folders (`.gitkeep`). Keep those folder names.
Do not modify `backend/`, `ai_ml/` or `database/`. If you believe the API needs a change, write it down in your final report instead.

---

# 2. STACK

React + Vite (JavaScript is fine; TypeScript optional), Tailwind CSS, react-router-dom, axios, recharts, `@supabase/supabase-js`.
Do not add heavy UI frameworks. Keep dependencies minimal.

Deployed backend (already live): API base `https://bizflow-backend-2onh.onrender.com`, Swagger `https://bizflow-backend-2onh.onrender.com/docs`, health `https://bizflow-backend-2onh.onrender.com/api/health`.
Use it as `VITE_API_URL` unless a local backend is running (the free Render plan can take ~1 minute to wake up on the first request).

Environment variables (Vite): `VITE_API_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`. Provide `frontend/.env.example`
(names only). Never hard-code URLs or keys. Never use `GROQ_API_KEY`, `DATABASE_URL` or the JWT secret in the frontend.

---

# 3. ARCHITECTURE RULES (CRITICAL)

1. **Supabase is only for authentication** (sign in, sign out, session). All business data comes from the FastAPI backend.
2. Every API request carries `Authorization: Bearer <supabase session access_token>` (fetch it per request via `getSession()`).
3. **Never send `business_id`** in any body or query — the backend resolves the business from the logged-in user and rejects unknown fields (422).
   Only if a user has several businesses, send the `X-Business-Id` header (needed on `400 business_required`).
4. **Never compute financial numbers in the frontend.** Receivables, payables, overdue, outstanding balance, invoice status,
   monthly totals and forecasts all come from the API. The frontend only formats and charts them.
5. Errors arrive as `{"error": {"code", "message", "details"}}`. Implement one axios interceptor that maps codes to friendly
   messages (see the error table in `backend/README.md`). On `401` sign out and redirect to login.
6. Money: JSON numbers; format with `Intl.NumberFormat('en-IN', { style: 'currency', currency })`. Send amounts with at most 2 decimals.
7. CORS: the backend only accepts origins listed in `ALLOWED_ORIGINS`. Dev origin is `http://localhost:5173`.

---

# 4. WHAT TO BUILD

Implement the services layer first (`src/services/*.js`: `supabase`, `api`, `invoices`, `payments`, `expenses`, `analytics`, `cash`, `assistant`),
then the pages, then shared components. Screens (details in `frontend/README.md` section 5):

1. **Login** + auth guard + logout.
2. **Dashboard** — receivables, payables, sales, expenses, operating surplus (label: *estimate, not profit*), overdue table, monthly chart.
3. **Upload Invoice** (the hero flow) — upload -> loading state -> **editable review form** with warnings -> explicit **Confirm & Save**.
4. **Invoices** list with filters + pagination; **Invoice detail** with payments, record-payment modal, edit, delete.
5. **Expenses** — list, add (paid/unpaid), mark as paid.
6. **Cash flow** — opening cash form (month-end date) + forecast chart with assumptions, warnings and disclaimer.
7. **Assistant** — chat UI with suggested questions, `answer`, `tool_used`, `data_used`, `follow_up`.

## The invoice review flow — get this exactly right

1. `POST /api/invoices/extract` (multipart, field name `file`; PDF/JPG/PNG, max 10 MB). **Nothing is saved.**
2. Response has `extraction_id`, `extracted_fields`, `warnings[]`, `extraction_status` (`ok` | `ai_extraction_failed`), `expires_at`.
3. Show an editable form prefilled from `extracted_fields`; show `warnings` next to the fields (`severity` = `warning` | `error`).
   If `ai_extraction_failed`: empty form + "automatic extraction failed, enter details manually".
4. User edits, then clicks **Confirm & Save** -> `POST /api/invoices` with `confirmed: true`, the edited fields and `extraction_id`.
5. Handle: `422 invalid_invoice` (show `details`), `409 duplicate_invoice`, `409 extraction_already_used`,
   `410 extraction_expired` (ask to upload again), `413`, `415`.
6. Never auto-submit step 4.

## Cash-flow rules

- `GET /api/forecast` returns `409 opening_cash_required` until opening cash exists -> show the opening-cash form (not an error page).
- Opening cash date must be a **month-end** (validate in the form: last day of month); amount may be negative.
- Always display `assumptions`, `warnings` and `disclaimer`; label as an estimate. If `insufficient_data` is true show an explanation instead of a chart.

---

# 5. UX / QUALITY REQUIREMENTS

- Loading, empty and error states on every screen. The backend runs on Render's free plan: the first request after idle can take ~1 minute
  and OCR/extraction up to ~60 s — show "waking up the server…" style feedback.
- Mobile-friendly responsive layout. Clean, professional finance look (not a generic template); consistent status badges
  (`unpaid`, `partially_paid`, `paid`, `needs_review`).
- Receivables and payables are never added together.
- Do not expose the token in logs or the UI. Escape/handle user-provided text safely (React default is fine; never use `dangerouslySetInnerHTML`).
- Accessible forms (labels, keyboard use, visible focus).

---

# 6. TESTING AND VERIFICATION

1. `npm run build` must pass with no errors; `npm run lint` if configured.
2. Use the deployed backend URL above (or run it locally: `cd backend && uvicorn app.main:app --reload`), log in as the seeded demo user and verify:
   - Dashboard shows receivables **45,000** and payables **20,000** (demo seed "Sen Electricals").
   - Recording a 10,000 payment on INV-102 makes receivables **35,000**.
   - Uploading `sample_data/invoices/sales_INV-103_total_mismatch.png` shows a validation warning.
   - Forecast works with the seeded opening cash (150,000 on 2026-10-31); a business without opening cash shows the setup form.
3. Optionally add a few component/unit tests (Vitest) for the API error mapping and the review form.
4. Do not claim something works unless you actually ran it. If the backend/Supabase is not reachable from your environment, say so
   and verify with mocked responses, clearly stating that.

---

# 7. IMPLEMENTATION RULES

1. Inspect before editing; keep the `frontend/src/{components,pages,services}` layout.
2. Do not touch `backend/`, `ai_ml/`, `database/`.
3. No fake financial data in production code (demo data lives in the database seed).
4. No secrets in the repo; `.env` is git-ignored, `.env.example` has names only.
5. Keep components small and reusable; keep API calls only inside `src/services`.
6. Do not commit or push unless explicitly asked.
7. Update `frontend/README.md` with the real run/build/deploy instructions, and add screenshots if possible.

---

# 8. FINAL REPORT (what to send back)

1. Files created / changed.
2. Pages and the endpoints each one uses.
3. How to run and build; environment variables needed.
4. What you verified for real, and with which data (and what you could not verify).
5. Deviations from `frontend/README.md`, API gaps or bugs found (do not silently work around backend problems).
6. Remaining TODOs, e.g. no signup/onboarding endpoint yet (new users get `403 no_business_access`), uploaded invoice files not downloadable.

---

# FINAL INSTRUCTION

**Start by reading the files in section 1, then build the app.** The backend contract in `backend/README.md` is the source of truth.
