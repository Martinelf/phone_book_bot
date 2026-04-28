from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from typing import Any

from phonebook.config import get_settings
from phonebook.db import execute_query
from phonebook.permissions import DEFAULT_ROLE, normalize_role

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


def _load_user_record(source: str, external_user_id: str) -> dict[str, Any] | None:
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
        LIMIT 1
    """
    return execute_query(query, (source, external_user_id), fetch="one")


def _load_user_access(source: str, external_user_id: str) -> dict[str, Any] | None:
    row = _load_user_record(source, external_user_id)
    if not row or not row.get("is_active"):
        return None
    return row


def _normalize_external_user_id(value: str | int) -> str:
    normalized = str(value).strip()
    if not normalized or not re.fullmatch(r"\d+", normalized):
        raise ValueError("external_user_id must contain digits only")
    return normalized


def grant_user_access(
    *,
    source: str,
    external_user_id: str | int,
    role: str | None = None,
    display_name: str | None = None,
    comment: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    schema = settings["pg_schema"]
    table = settings["auth_max_table"]
    normalized_user_id = _normalize_external_user_id(external_user_id)
    normalized_role = normalize_role(role or DEFAULT_ROLE)

    query = f"""
        INSERT INTO {schema}.{table} (
            source,
            external_user_id,
            display_name,
            role,
            is_active,
            comment
        )
        VALUES (%s, %s, %s, %s, TRUE, %s)
        ON CONFLICT (source, external_user_id)
        DO UPDATE SET
            display_name = EXCLUDED.display_name,
            role = EXCLUDED.role,
            is_active = TRUE,
            comment = EXCLUDED.comment
    """
    execute_query(
        query,
        (
            source,
            normalized_user_id,
            (display_name or "").strip() or None,
            normalized_role,
            (comment or "").strip() or None,
        ),
    )

    row = _load_user_record(source, normalized_user_id)
    if not row:
        raise RuntimeError("Could not load granted user access record")
    return row


def revoke_user_access(*, source: str, external_user_id: str | int) -> bool:
    settings = get_settings()
    schema = settings["pg_schema"]
    table = settings["auth_max_table"]
    normalized_user_id = _normalize_external_user_id(external_user_id)
    existing = _load_user_record(source, normalized_user_id)
    if not existing:
        return False

    query = f"""
        UPDATE {schema}.{table}
        SET is_active = FALSE
        WHERE source = %s
          AND external_user_id = %s
    """
    execute_query(query, (source, normalized_user_id))
    return True


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
