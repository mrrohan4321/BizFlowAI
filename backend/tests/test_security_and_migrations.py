from app import config
from app.db.database import get_cursor
from app.db.migrate import DB_DIR


def test_every_table_has_row_level_security():
    """Supabase's public REST API must not be able to read these tables with the anon key."""
    with get_cursor() as cur:
        cur.execute("SELECT c.relname, c.relrowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = %s AND c.relkind = 'r'", (config.DB_SCHEMA,))
        rows = cur.fetchall()
    assert rows, "no tables found"
    assert [r["relname"] for r in rows if not r["relrowsecurity"]] == []


def test_migrations_are_safe_to_run_again():
    from app.db import migrate
    assert migrate.run() == []                      # runner: nothing left to apply
    with get_cursor() as cur:                       # raw re-run (e.g. pasted into the SQL editor twice)
        for f in sorted((DB_DIR / "migrations").glob("*.sql")):
            cur.execute(f.read_text())
