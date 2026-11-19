-- Synthetic demo data for "Sen Electricals" (fictional). Safe to re-run: it wipes and
-- re-creates ONLY this demo business's records.
--
-- BEFORE RUNNING: replace demo_user below with YOUR Supabase Auth user id
-- (Supabase Dashboard -> Authentication -> Users -> copy the "User UID").
-- Run after schema.sql and migrations/001_backend_foundation.sql
-- (or just run:  cd backend && python -m app.db.migrate).
--
-- Known answers: receivables 45,000 | payables 20,000 | after a 10,000 payment on INV-102 receivables 35,000
--   INV-102 sales    30,000 ABC Constructions  unpaid   (due 2026-11-10 -> overdue after that date)
--   INV-103 sales    20,000 Raj Electricals    5,000 paid
--   PUR-201 purchase 20,000 XYZ Distributors   unpaid

DO $$
DECLARE
  demo_user UUID := '134e1685-7d75-4747-8d26-a629176e5d41';   -- <<< REPLACE ME
  bid UUID;
  inv UUID;
  m INT;
  mstart DATE;
BEGIN
  IF demo_user = '00000000-0000-0000-0000-000000000000' THEN
    RAISE EXCEPTION 'Edit seed_demo.sql: set demo_user to your Supabase Auth user id first.';
  END IF;

  SELECT id INTO bid FROM businesses WHERE name = 'Sen Electricals' ORDER BY created_at LIMIT 1;
  IF bid IS NULL THEN
    INSERT INTO businesses (name, currency, owner_user_id) VALUES ('Sen Electricals', 'INR', demo_user) RETURNING id INTO bid;
  END IF;
  INSERT INTO business_members (business_id, user_id, role) VALUES (bid, demo_user, 'owner') ON CONFLICT DO NOTHING;

  DELETE FROM invoice_extractions WHERE business_id = bid;
  DELETE FROM payments WHERE business_id = bid;
  DELETE FROM invoices WHERE business_id = bid;
  DELETE FROM expenses WHERE business_id = bid;
  DELETE FROM opening_cash_balances WHERE business_id = bid;
  DELETE FROM customers WHERE business_id = bid;
  DELETE FROM suppliers WHERE business_id = bid;

  INSERT INTO customers (business_id, name) VALUES (bid,'ABC Constructions'),(bid,'Raj Electricals'),(bid,'Metro Builders');
  INSERT INTO suppliers (business_id, name) VALUES (bid,'XYZ Distributors'),(bid,'Bharat Cables');

  -- Known-answer invoices
  INSERT INTO invoices (business_id, invoice_number, invoice_type, party_id, party_name, invoice_date, due_date, subtotal, tax_amount, total_amount) VALUES
    (bid,'INV-102','sales',(SELECT id FROM customers WHERE business_id=bid AND name='ABC Constructions'),'ABC Constructions','2026-10-26','2026-11-10',25423.73,4576.27,30000.00),
    (bid,'INV-103','sales',(SELECT id FROM customers WHERE business_id=bid AND name='Raj Electricals'),'Raj Electricals','2026-11-04','2026-11-25',16949.15,3050.85,20000.00),
    (bid,'PUR-201','purchase',(SELECT id FROM suppliers WHERE business_id=bid AND name='XYZ Distributors'),'XYZ Distributors','2026-11-08','2026-12-01',16949.15,3050.85,20000.00);
  INSERT INTO payments (business_id, invoice_id, amount, payment_date, method, reference, note)
  VALUES (bid,(SELECT id FROM invoices WHERE business_id=bid AND invoice_number='INV-103'),5000.00,'2026-11-05','UPI','UTR-DEMO-1','Part payment');

  -- Settled history Jun-Oct 2026 (so the forecast has data)
  FOR m IN 0..4 LOOP
    mstart := DATE '2026-06-01' + (m || ' month')::interval;

    INSERT INTO invoices (business_id, invoice_number, invoice_type, party_id, party_name, invoice_date, due_date, subtotal, tax_amount, total_amount)
    VALUES (bid,'INV-0'||(80+m),'sales',(SELECT id FROM customers WHERE business_id=bid AND name='Metro Builders'),'Metro Builders',
            mstart+4, mstart+19, 40000+m*2500, 0, 40000+m*2500) RETURNING id INTO inv;
    INSERT INTO payments (business_id, invoice_id, amount, payment_date, method) VALUES (bid, inv, 40000+m*2500, mstart+18, 'Bank transfer');

    INSERT INTO invoices (business_id, invoice_number, invoice_type, party_id, party_name, invoice_date, due_date, subtotal, tax_amount, total_amount)
    VALUES (bid,'PUR-1'||(10+m),'purchase',(SELECT id FROM suppliers WHERE business_id=bid AND name='Bharat Cables'),'Bharat Cables',
            mstart+2, mstart+20, 22000+m*1000, 0, 22000+m*1000) RETURNING id INTO inv;
    INSERT INTO payments (business_id, invoice_id, amount, payment_date, method) VALUES (bid, inv, 22000+m*1000, mstart+20, 'Bank transfer');

    INSERT INTO expenses (business_id, category, amount, expense_date, description, payment_status, paid_date) VALUES
      (bid,'Rent',8000,mstart+4,'Shop rent','paid',mstart+4),
      (bid,'Salaries',12000,mstart+26,'Staff salaries','paid',mstart+26),
      (bid,'Electricity',1800+m*100,mstart+9,'Electricity bill','paid',mstart+10),
      (bid,'Transport',1500,mstart+14,'Delivery transport','paid',mstart+14);
  END LOOP;

  -- Recorded but NOT yet paid: counts as an expense, not as cash outflow
  INSERT INTO expenses (business_id, category, amount, expense_date, description, payment_status)
  VALUES (bid,'Electricity',2200,'2026-11-09','November electricity bill (unpaid)','unpaid');

  -- Opening cash at the end of October (must be a month-end date)
  INSERT INTO opening_cash_balances (business_id, amount, as_of_date, note) VALUES (bid,150000.00,'2026-10-31','Demo opening balance');

  RAISE NOTICE 'Seeded Sen Electricals (business id %).', bid;
END $$;
