# Frontend (React + Vite + Tailwind)

**Status: NOT STARTED.** This folder only contains empty `src/components`, `src/pages`, `src/services` placeholders.
The backend, database and AI/ML parts are finished, tested and deployed - the frontend only has to *consume the API*.

> Using Claude / an AI coding assistant? Give it [FRONTEND_CLAUDE_HANDOFF.md](FRONTEND_CLAUDE_HANDOFF.md) as the first prompt
> (same idea as `ai_ml/BACKEND_CLAUDE_HANDOFF.md` that was used for the backend).

## 1. Read these first (10 minutes)

| File | Why |
|---|---|
| [../README.md](../README.md) | product flow, key money rules, setup |
| [../backend/README.md](../backend/README.md) | **the full API reference**: every endpoint, request/response, error codes |
| [../API-notes.md](../API-notes.md) | the shared contract (agree before changing) |
| `http://localhost:8000/docs` (or the Render URL + `/docs`) | live Swagger - try calls, see real JSON |
| [../sample_data/README.md](../sample_data/README.md) | invoices to use in the upload demo |

## 2. Create the app

```bash
cd frontend
npm create vite@latest . -- --template react
npm install
npm install tailwindcss @tailwindcss/vite recharts axios react-router-dom @supabase/supabase-js
```
(Tailwind: follow the current Vite guide; v4 uses the `@tailwindcss/vite` plugin.) Keep the existing `src/components`, `src/pages`,
`src/services` folders.

### Environment (`frontend/.env`, never commit)

```env
VITE_API_URL=http://localhost:8000          # or the Render URL
VITE_SUPABASE_URL=https://xxxx.supabase.co
VITE_SUPABASE_ANON_KEY=<anon/publishable key>   # public key only. NEVER put GROQ_API_KEY, DATABASE_URL or the JWT secret here
```
Add `frontend/.env.example` with the names only. The backend `ALLOWED_ORIGINS` must contain your dev/prod frontend URL
(`http://localhost:5173` is the default) or every call fails with a CORS error.

## 3. How the frontend talks to the system

```
Browser --Supabase JS--> Supabase Auth (login)  -> access_token
Browser --axios + Bearer access_token--> FastAPI backend --> Postgres / ai_ml / Groq
```

- **Supabase is used ONLY for login/logout/session.** All business data comes from the FastAPI backend. Never read
  tables with the Supabase client (RLS blocks it anyway).
- Every API call: `Authorization: Bearer <session.access_token>`. Get the token from `supabase.auth.getSession()` on each request
  (it auto-refreshes).
- **Never send `business_id`** (the backend rejects it with 422). Only if the user has several businesses, send header `X-Business-Id`.
- Errors always arrive as `{"error": {"code","message","details"}}`. Build one axios interceptor that turns this into a
  friendly message (code table in backend/README.md section 7). On 401 -> sign out and go to login.
- Money fields are JSON numbers. Display with `Intl.NumberFormat('en-IN', {style:'currency', currency:'INR'})`
  (the summary response has `currency`). **Do not calculate receivables/payables/overdue/forecast in the browser** - show what the API returns.

## 4. Suggested structure

```
src/
├── main.jsx, App.jsx            router + auth guard
├── services/
│   ├── supabase.js              createClient(VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY)
│   ├── api.js                   axios instance, token + error interceptors
│   ├── invoices.js  payments.js  expenses.js  analytics.js  assistant.js  cash.js
├── pages/
│   ├── Login.jsx
│   ├── Dashboard.jsx
│   ├── UploadInvoice.jsx        upload -> review -> confirm
│   ├── Invoices.jsx             list + filters;  InvoiceDetail.jsx (payments, edit, delete)
│   ├── Expenses.jsx
│   ├── CashFlow.jsx             opening cash + forecast
│   └── Assistant.jsx
└── components/                  Layout/Sidebar, StatCard, DataTable, StatusBadge, WarningList, MoneyInput, EmptyState, Loading, ErrorBanner, charts
```

## 5. Screens and the endpoints they use

| Screen | What to build | Endpoints |
|---|---|---|
| **Login** | email + password via `supabase.auth.signInWithPassword`; redirect to Dashboard; sign-out button | Supabase only |
| **Dashboard** | stat cards: sales total, expenses, **receivables**, **payables**, operating surplus (label it *estimate*, not profit); overdue count + table; monthly bar/line chart (sales vs expenses, cash in vs out); date range filter | `GET /analytics/summary`, `/analytics/overdue`, `/analytics/monthly` |
| **Upload invoice** (hero screen) | drag-drop PDF/JPG/PNG (<=10 MB) -> spinner (OCR can take 10-60 s) -> **editable review form** pre-filled from `extracted_fields`, warnings shown next to fields, `raw_text_preview` collapsible -> **Confirm & Save** button sends `confirmed: true` + `extraction_id`. If `extraction_status = "ai_extraction_failed"` show an empty form with "please enter manually". Handle 409/410/422 from confirm | `POST /invoices/extract`, `POST /invoices` |
| **Invoices** | table with filters (type, status, date range, party search), pagination (`limit`, `offset`, `total`), status badge (`unpaid` / `partially_paid` / `paid`), "needs review" badge when `review_status = needs_review` | `GET /invoices` |
| **Invoice detail** | fields, paid / outstanding, its payments, **Record payment** modal (amount <= outstanding), edit, delete (explain 409 if it has payments) | `GET /invoices/{id}`, `GET /payments?invoice_id=`, `POST /payments`, `PATCH /invoices/{id}`, `DELETE /invoices/{id}` |
| **Expenses** | list + add form (category, amount, date, paid/unpaid with `paid_date` shown only when paid), "mark as paid" action | `GET/POST /expenses`, `PATCH /expenses/{id}` |
| **Cash flow** | form to set **opening cash** (amount + a **month-end** date; show the latest saved value) -> forecast chart (`periods` + `values`) with `assumptions`, `warnings` and the `disclaimer` always visible. If the API returns `409 opening_cash_required` show the opening-cash form, not an error. Selectors for `months` (1-12) and `window` | `PUT/GET /opening-cash`, `GET /forecast` |
| **Assistant** | chat UI; suggested questions ("How much do customers owe me?", "Which invoices are overdue?", "How did my business perform?", "What is my expected cash flow?"); show `answer`, small "calculated by: tool_used" note, optional `data_used` table, clickable `follow_up`; handle `insufficient_data` and 502/503 politely | `POST /assistant/chat` |

### Non-negotiable UX rules
1. **Never auto-save** extracted data. The user must review and click Confirm.
2. Show validation `warnings` (severity `warning` / `error`); `error` severity blocks saving (422 `invalid_invoice` -> show `details`).
3. Receivables and payables are shown separately, never summed.
4. Forecast is always labelled "estimate" with its assumptions and disclaimer. Do not show a forecast without opening cash.
5. Loading, empty and error states on every screen (backend on Render free plan can take ~1 min on the first call - show "waking up the server...").
6. Mobile-friendly layout (judges may open it on a phone).
7. Do not log or display the access token.

## 6. Demo / test data

Log in with the user whose UID was put into `database/seed_demo.sql` ("Sen Electricals"). Expected dashboard: receivables **45,000**,
payables **20,000**; after recording a 10,000 payment on INV-102 receivables become **35,000**. Upload files from `sample_data/invoices/`.

## 7. Running and deploying

```bash
npm run dev        # http://localhost:5173  (needs backend running on VITE_API_URL)
npm run build      # outputs dist/
```
Deploy suggestion: Vercel / Netlify / Render Static Site with env vars `VITE_API_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`.
Then add the deployed URL to the backend's `ALLOWED_ORIGINS` on Render. SPA routing needs a rewrite of all paths to `index.html`.

## 8. Definition of done

- [ ] Login / logout works, protected routes redirect to login.
- [ ] Upload -> review -> confirm -> appears in Invoices; duplicate number shows a friendly message.
- [ ] Record payment updates status and the dashboard.
- [ ] Expenses (paid/unpaid) work; opening cash + forecast work; the 409 case is handled.
- [ ] Assistant answers the 5 example questions.
- [ ] No hard-coded API URL or keys; `.env.example` present; `.env` not committed.
- [ ] This README updated with real run/deploy instructions, screenshots and any deviations from the plan above.

## 9. Open questions to settle with the backend owner

- Signup / "create my business" has **no endpoint yet** (a new Supabase user gets `403 no_business_access` until a `business_members` row exists).
  Either keep using seeded demo users, or ask for a small onboarding endpoint.
- Uploaded invoice files cannot be re-downloaded (only `has_file` is returned).
- Customers / suppliers tables exist but have no endpoints; party is a free-text `party_name`.
