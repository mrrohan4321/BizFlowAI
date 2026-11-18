-- 001_backend_foundation.sql
-- Additive migration on top of database/schema.sql. Does not drop or rewrite
-- existing tables. Safe to run once; tracked by backend/app/db/migrate.py.

-- 1. Business membership (users come from the external auth provider;
--    user_id is the JWT "sub" claim, so there is intentionally no users table).
CREATE TABLE IF NOT EXISTS business_members (
  business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  user_id UUID NOT NULL,
  role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('owner','admin','member')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (business_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_business_members_user ON business_members(user_id);

-- Existing owners become members automatically.
INSERT INTO business_members (business_id, user_id, role)
SELECT id, owner_user_id, 'owner' FROM businesses WHERE owner_user_id IS NOT NULL
ON CONFLICT DO NOTHING;

ALTER TABLE businesses
  ADD COLUMN IF NOT EXISTS contact TEXT,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

-- 2. Invoices: GST split, notes, review status, timestamps.
ALTER TABLE invoices
  ADD COLUMN IF NOT EXISTS cgst NUMERIC(14,2) CHECK (cgst IS NULL OR cgst >= 0),
  ADD COLUMN IF NOT EXISTS sgst NUMERIC(14,2) CHECK (sgst IS NULL OR sgst >= 0),
  ADD COLUMN IF NOT EXISTS igst NUMERIC(14,2) CHECK (igst IS NULL OR igst >= 0),
  ADD COLUMN IF NOT EXISTS gstin TEXT,
  ADD COLUMN IF NOT EXISTS notes TEXT,
  ADD COLUMN IF NOT EXISTS review_status TEXT NOT NULL DEFAULT 'confirmed'
    CHECK (review_status IN ('confirmed','needs_review')),
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE invoices
  ADD CONSTRAINT invoices_total_nonneg CHECK (total_amount >= 0) NOT VALID;

-- One invoice number per business per type (a sales and a purchase invoice
-- may legitimately share a number).
CREATE UNIQUE INDEX IF NOT EXISTS uq_invoices_business_type_number
  ON invoices (business_id, invoice_type, invoice_number);
CREATE INDEX IF NOT EXISTS idx_invoices_business_due ON invoices (business_id, due_date);
CREATE INDEX IF NOT EXISTS idx_invoices_business_date ON invoices (business_id, invoice_date);

-- 3. Payments: reference number, timestamps. Partial / multiple payments per
--    invoice are already supported (no uniqueness on invoice_id).
ALTER TABLE payments
  ADD COLUMN IF NOT EXISTS reference TEXT,
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
CREATE INDEX IF NOT EXISTS idx_payments_business_date ON payments (business_id, payment_date);

-- 4. Expenses: separate expense recognition from actual cash movement.
--    Existing rows default to 'unpaid' so they are NOT counted as cash
--    outflow until someone confirms they were paid.
ALTER TABLE expenses
  ADD COLUMN IF NOT EXISTS payment_status TEXT NOT NULL DEFAULT 'unpaid'
    CHECK (payment_status IN ('unpaid','paid')),
  ADD COLUMN IF NOT EXISTS paid_date DATE,
  ADD COLUMN IF NOT EXISTS notes TEXT,
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE expenses
  ADD CONSTRAINT expenses_paid_has_date
  CHECK (payment_status <> 'paid' OR paid_date IS NOT NULL);
CREATE INDEX IF NOT EXISTS idx_expenses_business_date ON expenses (business_id, expense_date);

-- 5. Opening cash balance (never assumed to be zero).
--    The latest row with as_of_date <= end of last history month is used.
CREATE TABLE IF NOT EXISTS opening_cash_balances (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  amount NUMERIC(14,2) NOT NULL,           -- may be negative (overdraft)
  as_of_date DATE NOT NULL,
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (business_id, as_of_date)
);

-- 6. Staging table for AI extraction: nothing in `invoices` is written until
--    the user confirms. Rows expire and are single-use.
CREATE TABLE IF NOT EXISTS invoice_extractions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  user_id UUID NOT NULL,
  stored_file TEXT NOT NULL,               -- server-generated name, never user input
  original_filename TEXT,
  extracted JSONB NOT NULL,
  issues JSONB NOT NULL DEFAULT '[]',
  needs_review BOOLEAN NOT NULL DEFAULT TRUE,
  consumed_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_invoice_extractions_business ON invoice_extractions (business_id);
