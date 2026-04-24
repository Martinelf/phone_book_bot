from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from phonebook.config import get_settings
from phonebook.db import execute_query

logger = logging.getLogger(__name__)


@dataclass
class AuthDecision:
    allowed: bool
    source: str
    external_user_id: str | None
    role: str | None = None
    reason: str = "unknown"


def _is_enabled(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _extract_nested_attr(candidate: Any, path: tuple[str, ...]) -> Any:
    current = candidate
    for name in path:
        if current is None or not hasattr(current, name):
            return None
        current = getattr(current, name)
    return current


def extract_max_user_id(event: Any) -> str | None:
    candidate_paths = (
        ("user_id",),
        ("sender_id",),
        ("sender", "user_id"),
        ("sender", "id"),
        ("from_user", "user_id"),
        ("from_user", "id"),
        ("user", "user_id"),
        ("user", "id"),
        ("message", "user_id"),
        ("message", "sender_id"),
        ("message", "sender", "user_id"),
        ("message", "sender", "id"),
        ("message", "from_user", "user_id"),
        ("message", "from_user", "id"),
        ("message", "user", "user_id"),
        ("message", "user", "id"),
        ("message", "author", "user_id"),
        ("message", "author", "id"),
    )

    for path in candidate_paths:
        value = _extract_nested_attr(event, path)
        if value is None:
            continue
        normalized = str(value).strip()
        if normalized:
            return normalized
    return None


def _load_user_access(source: str, external_user_id: str) -> dict[str, Any] | None:
    settings = get_settings()
    schema = settings["pg_schema"]
    table = settings["auth_max_table"]
    query = f"""
        SELECT
            source,
            external_user_id,
            display_name,
            role,
            is_active
        FROM {schema}.{table}
        WHERE source = %s
          AND external_user_id = %s
          AND is_active = TRUE
        LIMIT 1
    """
    return execute_query(query, (source, external_user_id), fetch="one")


def authorize_max_event(event: Any) -> AuthDecision:
    settings = get_settings()
    if not _is_enabled(settings["auth_max_enabled"]):
        return AuthDecision(allowed=True, source="max", external_user_id=None, role="bypass", reason="disabled")

    external_user_id = extract_max_user_id(event)
    if not external_user_id:
        logger.warning("MAX auth denied: user id is missing in event")
        return AuthDecision(
            allowed=False,
            source="max",
            external_user_id=None,
            reason="missing_user_id",
        )

    try:
        row = _load_user_access("max", external_user_id)
    except Exception as exc:
        logger.exception("MAX auth failed for user_id=%s: %r", external_user_id, exc)
        return AuthDecision(
            allowed=False,
            source="max",
            external_user_id=external_user_id,
            reason="auth_backend_error",
        )

    if not row:
        logger.info("MAX auth denied: user_id=%s is not in allowlist", external_user_id)
        return AuthDecision(
            allowed=False,
            source="max",
            external_user_id=external_user_id,
            reason="not_allowed",
        )

    return AuthDecision(
        allowed=True,
        source="max",
        external_user_id=external_user_id,
        role=(row.get("role") or "user"),
        reason="allowed",
    )
