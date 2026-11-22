# 🔌 services/

The only place that talks to the outside world. Pages never call axios or Supabase directly.

| File | Contents |
|---|---|
| `supabase.js` | Supabase client (login/session only), `signIn`, `signOut`, `configured` flag |
| `api.js` | axios instance for `<VITE_API_URL>/api`: adds `Authorization: Bearer <token>` (and `X-Business-Id` if set), maps `{error:{code,message}}` to friendly errors, signs out on 401 |
| `invoices.js` | `listInvoices`, `getInvoice`, `extractInvoice` (multipart `file`), `saveInvoice`, `updateInvoice`, `deleteInvoice` |
| `payments.js` | `listPayments`, `createPayment` |
| `expenses.js` | `listExpenses`, `addExpense`, `markExpensePaid` |
| `cash.js` | `getOpeningCash`, `saveOpeningCash`, `getForecast` |
| `analytics.js` | `getSummary`, `getOverdue`, `getMonthly` |
| `assistant.js` | `askAssistant` |

Notes: do not set `Content-Type` yourself for the file upload (the browser adds the multipart boundary). Never send `business_id` in a body (the backend rejects it).
Endpoint details: [../../../backend/README.md](../../../backend/README.md).
