from __future__ import annotations

import json
import logging
from typing import Any

from phonebook.config import get_settings
from phonebook.db import execute_query

logger = logging.getLogger(__name__)


def _is_enabled(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def write_query_audit(
    *,
    source: str,
    external_user_id: str | None,
    role: str | None,
    query_text: str,
    parsed_query: dict[str, Any],
    decision_status: str,
    decision_message: str,
    confidence: float,
    top_ids: list[int],
) -> None:
    settings = get_settings()
    if not _is_enabled(settings["audit_enabled"]):
        return

    schema = settings["pg_schema"]
    table = settings["audit_table"]
    query = f"""
        INSERT INTO {schema}.{table} (
            source,
            external_user_id,
            role,
            query_text,
            parsed_query,
            decision_status,
            decision_message,
            confidence,
            top_ids
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            CAST(%s AS jsonb),
            %s,
            %s,
            %s,
            CAST(%s AS jsonb)
        )
    """

    try:
        execute_query(
            query,
            (
                source,
                external_user_id,
                role,
                query_text,
                json.dumps(parsed_query, ensure_ascii=False),
                decision_status,
                decision_message,
                round(confidence, 4),
                json.dumps(top_ids),
            ),
        )
    except Exception as exc:
        logger.warning("Could not write query audit log: %r", exc)
