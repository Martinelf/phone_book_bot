from __future__ import annotations

import pg8000

from phonebook.config import get_settings


def get_connection(database: str | None = None):
    settings = get_settings()
    return pg8000.connect(
        database=database or settings["pg_db"],
        user=settings["pg_user"],
        password=settings["pg_password"],
        host=settings["pg_host"],
        port=int(settings["pg_port"]),
    )


def execute_query(query, params=None, fetch: str = "all"):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if params is None:
                cur.execute(query)
            else:
                cur.execute(query, params)
            if query.strip().lower().startswith("select"):
                columns = [desc[0] for desc in cur.description] if cur.description else []
                if fetch == "one":
                    row = cur.fetchone()
                    return dict(zip(columns, row)) if row else None
                rows = cur.fetchall()
                return [dict(zip(columns, row)) for row in rows]
            conn.commit()
            return None
    finally:
        conn.close()
