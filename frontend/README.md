# Frontend (React + Vite + Tailwind)

**Owner: Ronit Jana (Member 1).** A single-page app for the BizFlow AI backend: login, overview dashboard,
invoice upload with human review, invoices and payments, expenses, opening cash and forecast, and the finance assistant.

> **Status: implemented.** `npm run build` passes (checked on 20 Nov 2026). The authenticated end-to-end flow with the real demo login
> still has to be ticked off against the deployed backend: see [section 8](#8-verification-checklist). Do not describe the demo numbers as
> verified until you have run that checklist.

The frontend only **shows data and collects input**. It never calculates receivables, payables, overdue days, balances or forecasts
(that is `ai_ml/`, reached through the backend), never talks to Groq, and never sends a `business_id`.

## 1. Run it

Requirements: **Node.js 20.19+ or 22.12+** (Node 24 also works).

```bash
cd frontend
npm install
cp .env.example .env        # then fill the three values below
npm run dev                 # http://localhost:5173
```

`frontend/.env` (public values only; ask Rohan for the Supabase project URL and the public anon/publishable key):

```env
VITE_API_URL=https://bizflow-backend-2onh.onrender.com     # deployed backend, or http://localhost:8000
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_SUPABASE_ANON_KEY=YOUR_PUBLIC_ANON_KEY
```

**Never** put the database password, the JWT secret or the Groq key here. Anything starting with `VITE_` is visible in the browser.
If a variable is missing the app shows a clear "Supabase is not configured" message instead of crashing.

The backend must allow your origin: `http://localhost:5173` is allowed by default; for a deployed frontend the backend owner must add its
HTTPS URL to `ALLOWED_ORIGINS` on Render, otherwise every request fails with a CORS error.
Log in with the Supabase demo user linked to "Sen Electricals" (see [../database/README.md](../database/README.md)).
Render's free plan sleeps: the first request can take up to a minute (the UI says "the server may be waking up").

## 2. Scripts

| Command | What it does |
|---|---|
| `npm run dev` | dev server on port 5173 (`--host 0.0.0.0`) |
| `npm run build` | production build into `dist/` |
| `npm run preview` | serve the built `dist/` locally |

`package.json` also lists `npm run lint`, but ESLint is not installed or configured, so it will not work yet.
There are no automated frontend tests yet.

## 3. Screens and the API calls they make

| Route | Page file | Calls |
|---|---|---|
| `/login` | `pages/Login.jsx` | Supabase `signInWithPassword` |
| `/` Overview | `pages/Dashboard.jsx` | `GET /api/analytics/summary`, `/analytics/overdue`, `/analytics/monthly` (bar charts, date filter) |
| `/upload` | `pages/UploadInvoice.jsx` | `POST /api/invoices/extract`, then `POST /api/invoices` **only after the user confirms** |
| `/invoices` | `pages/Invoices.jsx` | `GET /api/invoices` (filters, pagination) |
| `/invoices/:id` | `pages/InvoiceDetail.jsx` | `GET/PATCH/DELETE /api/invoices/{id}`, `GET/POST /api/payments` |
| `/expenses` | `pages/Expenses.jsx` | `GET/POST /api/expenses`, `PATCH /api/expenses/{id}` (mark paid) |
| `/cash-flow` | `pages/CashFlow.jsx` | `GET/PUT /api/opening-cash`, `GET /api/forecast` (area chart) |
| `/assistant` | `pages/Assistant.jsx` | `POST /api/assistant/chat` |

All routes except `/login` are behind an auth guard (`App.jsx`). Unknown paths redirect to `/`.
The full API reference (bodies, responses, error codes) is in [../backend/README.md](../backend/README.md); the short contract is [../API-notes.md](../API-notes.md).

## 4. Folder structure

```
frontend/
├── index.html, vite.config.js      Vite + React + Tailwind v4 plugin, dev port 5173
├── vercel.json                     rewrites every path to /index.html (needed for React Router)
├── .env.example                    names of the 3 VITE_ variables
├── FRONTEND_CLAUDE_HANDOFF.md      the brief used to build this app
├── public/favicon.svg
└── src/
    ├── main.jsx, App.jsx           router, auth guard, app shell (sidebar, top bar, mobile menu)
    ├── theme.js                    light / night theme (saved in localStorage as "bizflow-theme")
    ├── style.css, dark.css         styles; dark.css holds the night-theme overrides
    ├── services/                   API + auth code only (no UI)        -> services/README.md
    ├── components/UI.jsx           shared UI pieces                    -> components/README.md
    └── pages/                      one file per screen                 -> pages/README.md
```

## 5. How it talks to the backend

```
Browser --Supabase JS--> Supabase Auth (login)  -> access_token
Browser --axios + Bearer access_token--> FastAPI backend --> Postgres / ai_ml / Groq
```

- `services/supabase.js` creates the Supabase client (used **only** for login, logout and the session). Business data is never read with the Supabase client (RLS blocks it anyway).
- `services/api.js` is the one axios instance (`<VITE_API_URL>/api`, 110 s timeout). The request interceptor fetches a fresh token from
  `supabase.auth.getSession()` for **every** call. If there is no session it raises the `bizflow:unauthorized` event and the app returns to Login.
- The response interceptor turns the backend's `{"error": {"code","message","details"}}` into a friendly `Error` (`apiError()`), with messages for each code
  (for example `overpayment`, `duplicate_invoice`, `opening_cash_required`). A `401` signs the user out.
- Optional multi-business support: `setBusinessId(id)` stores an id in `sessionStorage` and sends it as `X-Business-Id`. There is no business picker screen yet.
- Money is displayed with `money()` in `components/UI.jsx` (Indian formatting, INR).

## 6. Safety rules built into the UI

1. **Never auto-save.** Extracted data goes into an editable review form; saving needs the explicit **Confirm** button, which sends `confirmed: true` (+ `extraction_id`).
2. If extraction fails (`ai_extraction_failed`) the form is empty and the user types the invoice manually.
3. Validation warnings from the API are shown next to the form; errors block saving (the backend answers `422 invalid_invoice`).
4. The forecast and the operating surplus are labelled as estimates; assumptions, warnings and the disclaimer are shown. A `409 opening_cash_required` shows the opening-cash form, not an error.
5. Receivables and payables are shown separately, never added.
6. Money from `extracted_fields` can arrive as text (for example `"1180.00"`); the form converts it to a number before saving.
7. No secrets in the code; the access token is never logged or shown.

## 7. Build and deploy

```bash
npm run build      # outputs dist/
```

Host `dist/` on Vercel, Netlify or any static host. Set the same three `VITE_` variables in the host's dashboard and keep the SPA rewrite
(`vercel.json` already contains it; other hosts need an equivalent "all paths -> /index.html" rule). Then give the deployed HTTPS URL to the backend owner for `ALLOWED_ORIGINS`.
The JS bundle currently triggers a Vite size warning; code-splitting is a possible later optimisation.

## 8. Verification checklist

Run against the deployed backend with the seeded demo user and tick each line before submission:

- [ ] Login works, a wrong password shows an error, sign-out returns to Login, protected pages redirect when logged out
- [ ] Overview: receivables **45,000**, payables **20,000**, the overdue invoice is listed
- [ ] Upload `sample_data/invoices/sales_INV-103_total_mismatch.png`: a warning is shown and nothing is saved until Confirm
- [ ] Confirm a new invoice (use a number that is not in the seed): it appears in Invoices; a duplicate number shows a friendly message
- [ ] Record a 10,000 payment on INV-102: status changes and receivables become **35,000**; a payment above the outstanding amount is rejected
- [ ] Add an expense as unpaid, then mark it paid
- [ ] Cash flow: opening cash 150,000 at 2026-10-31 shows a forecast with assumptions and disclaimer
- [ ] Assistant answers: receivables, overdue invoices, expected cash flow; "hi" gets a friendly reply
- [ ] The layout works on a phone-sized screen and the night theme toggle works

## 9. Known gaps (backend or frontend)

- No sign-up / "create my business" endpoint: a new Supabase user gets `403 no_business_access` until a `business_members` row exists (done by SQL).
- Uploaded invoice files cannot be downloaded again (the API only returns `has_file`).
- The backend has no endpoint to delete payments or expenses; the expense list shows up to 100 records because the API returns no total for expenses.
- The sidebar shows a fixed "My business" label (the API has no endpoint that returns the business name).
- No automated frontend tests, ESLint is not set up, and the bundle is not code-split.
