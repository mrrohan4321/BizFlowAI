# db/

- `database.py`: `get_connection()` is one transaction (commit on success, rollback on error);
  `get_cursor()` wraps it for single queries. Rows come back as dicts (`RealDictCursor`).
  `DB_SCHEMA` is used only by tests to run inside a temporary schema.
- `migrate.py`: `python -m app.db.migrate` (run from `backend/`). See `database/README.md` for details.

A new connection is opened per call (no pool). With Supabase use a connection string that suits a server (pooler is fine;
`SET LOCAL` is used for the test schema so it stays pooler-safe).
