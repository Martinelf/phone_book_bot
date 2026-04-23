from __future__ import annotations

from pathlib import Path
import sys

import pg8000

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phonebook.config import get_settings


def _execute_sql_script(cur, script: str) -> None:
    statements = [part.strip() for part in script.split(";") if part.strip()]
    for statement in statements:
        cur.execute(statement)


def ensure_database_exists() -> None:
    settings = get_settings()
    admin_db = settings["pg_admin_db"]
    target_db = settings["pg_db"]

    conn = pg8000.connect(
        database=admin_db,
        user=settings["pg_user"],
        password=settings["pg_password"],
        host=settings["pg_host"],
        port=int(settings["pg_port"]),
    )
    conn.autocommit = True

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
            exists = cur.fetchone() is not None
            if not exists:
                cur.execute(f'CREATE DATABASE "{target_db}"')
                print(f"Created database: {target_db}")
            else:
                print(f"Database already exists: {target_db}")
    finally:
        conn.close()


def apply_schema() -> None:
    settings = get_settings()
    sql_path = Path(__file__).resolve().parents[1] / "sql" / "synthetic_phonebook.sql"
    script = sql_path.read_text(encoding="utf-8")

    conn = pg8000.connect(
        database=settings["pg_db"],
        user=settings["pg_user"],
        password=settings["pg_password"],
        host=settings["pg_host"],
        port=int(settings["pg_port"]),
    )

    try:
        with conn.cursor() as cur:
            _execute_sql_script(cur, script)
            cur.execute("SELECT COUNT(*) FROM bot_test.phone_directory")
            employee_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM bot_test.departments")
            department_count = cur.fetchone()[0]
            conn.commit()
            print(f"Synthetic data loaded: {employee_count} employees, {department_count} departments")
    finally:
        conn.close()


if __name__ == "__main__":
    ensure_database_exists()
    apply_schema()
