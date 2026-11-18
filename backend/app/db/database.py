"""Plain psycopg2 access (the project uses raw SQL, no ORM)."""
import re
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

from app import config

psycopg2.extras.register_uuid()


def _connect():
    if not config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(config.DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


@contextmanager
def get_connection():
    """One transaction: commit on success, rollback on any exception."""
    conn = _connect()
    try:
        if config.DB_SCHEMA:
            if not re.fullmatch(r"[a-z0-9_]+", config.DB_SCHEMA):
                raise RuntimeError("Invalid DB_SCHEMA")
            with conn.cursor() as cur:  # SET LOCAL is pooler-safe (transaction scoped)
                cur.execute(f"SET LOCAL search_path TO {config.DB_SCHEMA}")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def get_cursor():
    with get_connection() as conn:
        with conn.cursor() as cur:
            yield cur
