# pages/

One file per screen. Each page loads its data through `src/services/*`, shows loading / empty / error states, and renders values exactly as the API returns them.

| File | Route | What it does |
|---|---|---|
| `Login.jsx` | `/login` | email + password sign-in with Supabase |
| `Dashboard.jsx` | `/` | summary cards (sales, expenses, receivables, payables, surplus estimate), overdue invoices, monthly charts, date filter |
| `UploadInvoice.jsx` | `/upload` | step 1 upload (PDF/JPG/PNG up to 10 MB), step 2 editable review form with warnings, explicit confirm. `invoicePayload()` builds the save body |
| `Invoices.jsx` | `/invoices` | list with filters and pagination, status and "needs review" badges |
| `InvoiceDetail.jsx` | `/invoices/:id` | fields, paid/outstanding, payments, record payment, edit, delete |
| `Expenses.jsx` | `/expenses` | list, add (paid/unpaid), mark paid |
| `CashFlow.jsx` | `/cash-flow` | opening cash form (month-end date) and forecast chart with assumptions, warnings, disclaimer |
| `Assistant.jsx` | `/assistant` | chat with suggested questions, `follow_up` button, "calculated by" note, optional data panel |

Adding a page: create the file here, add the route in `src/App.jsx`, add a menu entry in the `nav` list in `App.jsx`, and put its API calls in `src/services/`.
