"""Minimal migration runner: python -m app.db.migrate  (run from backend/).
Applies database/schema.sql if the DB is empty, then each database/migrations/*.sql once."""
from pathlib import Path

from app import config
from app.db.database import get_connection

DB_DIR = config.REPO_ROOT / "database"


def run() -> list[str]:
    applied: list[str] = []
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())")
            cur.execute("SELECT to_regclass('businesses') AS t")
            if cur.fetchone()["t"] is None:
                cur.execute((DB_DIR / "schema.sql").read_text())
                applied.append("schema.sql")
            cur.execute("SELECT name FROM schema_migrations")
            done = {r["name"] for r in cur.fetchall()}
            for f in sorted((DB_DIR / "migrations").glob("*.sql")):
                if f.name not in done:
                    cur.execute(f.read_text())
                    cur.execute("INSERT INTO schema_migrations(name) VALUES (%s)", (f.name,))
                    applied.append(f.name)
    return applied


if __name__ == "__main__":
    print("applied:", run() or "nothing (up to date)")
