# 🗄️ Database (Supabase PostgreSQL)

🌐 **Live API:** [bizflow-backend-2onh.onrender.com/docs](https://bizflow-backend-2onh.onrender.com/docs) · 🌍 **Live app:** [biz-flow-ai-xi.vercel.app](https://biz-flow-ai-xi.vercel.app/) · 🎬 **Demo video:** [YouTube](https://youtu.be/Tf-raKI9BRM)

**Owner: Rohan Adak (Member 2).**

Plain SQL, no ORM. The backend talks to it with psycopg2 (`backend/app/db/`).

## 📁 Files

| File | Purpose |
|---|---|
| `schema.sql` | Base tables (businesses, customers, suppliers, invoices, payments, expenses, forecasts). Applied only when the DB is empty |
| `migrations/001_backend_foundation.sql` | Adds `business_members`, GST columns, review status, payment/expense cash fields, `opening_cash_balances`, `invoice_extractions`, indexes, unique invoice number |
| `migrations/002_enable_rls.sql` | Enables Row Level Security on every table (blocks the public Supabase anon key) |
| `seed_demo.sql` | Fictional demo business "Sen Electricals" with known answers |

## 🛠️ Apply the schema

```bash
cd backend && python -m app.db.migrate
```
The runner creates `schema_migrations`, applies `schema.sql` if `businesses` does not exist, then every `migrations/*.sql`
in name order, **once each**. Render runs it on every deploy, so it is safe to re-run. Output: `applied: [...]`.

**Rules:** never edit a migration that has already been applied anywhere; add `003_*.sql` instead. Keep migrations additive
(`IF NOT EXISTS`) and idempotent. Every new table also needs `ENABLE ROW LEVEL SECURITY` (a backend test checks this).

## 🗄️ Tables

| Table | Key columns / notes |
|---|---|
| `businesses` | `name`, `currency` (default INR), `owner_user_id`, `contact`, `updated_at` |
| `business_members` | `(business_id, user_id)` PK, `role` owner/admin/member. `user_id` = Supabase JWT `sub` (no users table). **Defines who can access which business** |
| `customers`, `suppliers` | `business_id`, `name`, `contact`. Not used by the API yet (invoices store `party_name`) |
| `invoices` | `invoice_type` sales/purchase, number, party, dates, `subtotal`, `tax_amount`, `cgst/sgst/igst`, `gstin`, `total_amount`, `notes`, `file_path`, `review_status` confirmed/needs_review. **Unique `(business_id, invoice_type, invoice_number)`** |
| `payments` | `invoice_id`, `amount > 0`, `payment_date`, `method`, `reference`. Many per invoice (partial payments) |
| `expenses` | `category`, `amount`, `expense_date`, `payment_status` unpaid/paid, `paid_date` (required when paid) |
| `opening_cash_balances` | `amount` (may be negative), `as_of_date` (month-end), unique per `(business_id, as_of_date)` |
| `invoice_extractions` | staging area for AI extraction: `extracted` JSONB, `issues`, `expires_at`, `consumed_at`. Nothing reaches `invoices` until the user confirms |
| `forecasts` | reserved, unused (forecast is computed on demand) |
| `schema_migrations` | migration bookkeeping |

All money columns are `NUMERIC(14,2)`. Every business table has `business_id` and ON DELETE CASCADE from `businesses`.

## 🎬 Demo data

1. Create a user in Supabase Auth and copy the **User UID**.
2. Open `seed_demo.sql` and set `demo_user UUID := '...'` to that UID (the file currently contains the team's demo user UID; replace it if you use your own Supabase project or user).
3. Run the file in the Supabase SQL Editor (after migrating). Safe to re-run: it wipes and recreates only the "Sen Electricals" records.

Known answers after seeding (also checked by `backend/scripts/smoke_test.py`):

| Item | Value |
|---|---|
| INV-102 (sales, ABC Constructions) | 30,000 unpaid, due 2026-11-10 |
| INV-103 (sales, Raj Electricals) | 20,000 with 5,000 paid |
| PUR-201 (purchase, XYZ Distributors) | 20,000 unpaid |
| Receivables / payables | **45,000 / 20,000** (after a 10,000 payment on INV-102: receivables 35,000) |
| History | Jun-Oct 2026 settled invoices, payments and paid expenses; opening cash 150,000 on 2026-10-31 |

## 🔌 Onboarding a new real user (no API for this yet)

```sql
INSERT INTO businesses (name, owner_user_id) VALUES ('My Shop', '<supabase user uid>') RETURNING id;
INSERT INTO business_members (business_id, user_id, role) VALUES ('<business id>', '<supabase user uid>', 'owner');
```
Without the `business_members` row the user gets `403 no_business_access`. A proper "create my business" endpoint is a good
next backend task (see backend/README.md, known limitations).

## ☁️ Supabase notes

- Use the **connection pooler** string for `DATABASE_URL` on Render.
- The backend connects as the database owner (bypasses RLS). The frontend must **never** query tables directly through the
  Supabase client - it only uses Supabase for login and calls the FastAPI backend for all data.
