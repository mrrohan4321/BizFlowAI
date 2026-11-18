CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE businesses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_user_id UUID,
  name TEXT NOT NULL,
  currency TEXT NOT NULL DEFAULT 'INR',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE customers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  contact TEXT
);

CREATE TABLE suppliers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  contact TEXT
);

CREATE TABLE invoices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  invoice_number TEXT NOT NULL,
  invoice_type TEXT NOT NULL CHECK (invoice_type IN ('sales','purchase')),
  party_id UUID,
  party_name TEXT,
  invoice_date DATE,
  due_date DATE,
  subtotal NUMERIC(14,2),
  tax_amount NUMERIC(14,2),
  total_amount NUMERIC(14,2) NOT NULL,
  file_path TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
  amount NUMERIC(14,2) NOT NULL CHECK (amount > 0),
  payment_date DATE NOT NULL,
  method TEXT,
  note TEXT
);

CREATE TABLE expenses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  category TEXT NOT NULL,
  amount NUMERIC(14,2) NOT NULL CHECK (amount >= 0),
  expense_date DATE NOT NULL,
  description TEXT
);

CREATE TABLE forecasts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  forecast_month DATE NOT NULL,
  predicted_income NUMERIC(14,2),
  predicted_outflows NUMERIC(14,2),
  predicted_closing_cash NUMERIC(14,2),
  method TEXT,
  assumptions TEXT
);

CREATE INDEX idx_invoices_business ON invoices(business_id);
CREATE INDEX idx_payments_invoice ON payments(invoice_id);
CREATE INDEX idx_expenses_business ON expenses(business_id);
