-- 002_enable_rls.sql
-- Supabase exposes every table in the public schema through its REST API using the PUBLIC anon key.
-- Without Row Level Security anyone holding that key could read/write all business data directly,
-- bypassing this backend. Enabling RLS with NO policies denies anon/authenticated roles completely.
-- The backend connects with the database owner role (postgres), which bypasses RLS, so nothing changes for it.
-- Safe to re-run.
ALTER TABLE IF EXISTS businesses            ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS customers             ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS suppliers             ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS invoices              ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS payments              ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS expenses              ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS forecasts             ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS business_members      ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS opening_cash_balances ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS invoice_extractions   ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS schema_migrations     ENABLE ROW LEVEL SECURITY;
