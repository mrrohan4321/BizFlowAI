"""Plain psycopg2 access (the project uses raw SQL, no ORM)."""
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

from app import config


def _connect():
    if not config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(config.DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


@contextmanager
def get_connection():
    """One transaction: commit on success, rollback on any exception."""
    conn = _connect()
    try:
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
