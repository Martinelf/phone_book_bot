from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def load_env() -> None:
    root = Path(__file__).resolve().parents[1]
    env_path = root / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)


def get_settings() -> dict[str, str]:
    load_env()
    return {
        "pg_host": os.getenv("PG_HOST", "localhost"),
        "pg_port": os.getenv("PG_PORT", "5432"),
        "pg_db": os.getenv("PG_DB", "phone_book_demo"),
        "pg_admin_db": os.getenv("PG_ADMIN_DB", "postgres"),
        "pg_user": os.getenv("PG_USER", "postgres"),
        "pg_password": os.getenv("PG_PASSWORD", ""),
        "pg_schema": os.getenv("PG_SCHEMA", "bot_test"),
        "ollama_url": os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),
        "ollama_model": os.getenv("OLLAMA_MODEL", "qwen3.5:2b"),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "log_file": os.getenv("LOG_FILE", "logs/phonebook.log"),
        "max_token": os.getenv("MAX_TOKEN", ""),
        "max_skip_updates": os.getenv("MAX_SKIP_UPDATES", "true"),
        "auth_max_enabled": os.getenv("AUTH_MAX_ENABLED", "true"),
        "auth_max_table": os.getenv("AUTH_MAX_TABLE", "authorized_users"),
        "audit_enabled": os.getenv("AUDIT_ENABLED", "false"),
        "audit_table": os.getenv("AUDIT_TABLE", "query_audit_log"),
    }
