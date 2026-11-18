from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

from app.config import DATABASE_URL


@contextmanager
def get_cursor():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set in .env")
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
