from __future__ import annotations

import asyncio
import logging

from maxapi import Bot, Dispatcher
from maxapi.types import Command, MessageCreated

from phonebook.auth import AuthDecision, authorize_max_event, grant_user_access, revoke_user_access
from phonebook.bot import SearchContext, resolve_phonebook_query
from phonebook.config import get_settings
from phonebook.logging_config import configure_logging
from phonebook.permissions import KNOWN_ROLES, normalize_role

logger = logging.getLogger(__name__)
dp = Dispatcher()


def _ru(text: str) -> str:
    return text.encode("ascii").decode("unicode_escape")


def _format_person_name(row: dict) -> str:
    parts = [row["last_name"], row["first_name"]]
    if row.get("patronymic"):
        parts.append(row["patronymic"])
    return " ".join(parts)


def _render_result(row: dict, index: int) -> str:
    lines = [f"{index}. {_format_person_name(row)}"]
    if row.get("post"):
        lines.append(_ru(r"\u0414\u043e\u043b\u0436\u043d\u043e\u0441\u0442\u044c: ") + row["post"])
    if row.get("department_name"):
        lines.append(_ru(r"\u041e\u0442\u0434\u0435\u043b: ") + row["department_name"])
    if row.get("phone"):
        phone_line = _ru(r"\u0422\u0435\u043b\u0435\u0444\u043e\u043d: ") + row["phone"]
        if row.get("phone_ext"):
            phone_line += " " + _ru(r"\u0434\u043e\u0431. ") + row["phone_ext"]
        lines.append(phone_line)
    if row.get("mobile_phone"):
        lines.append(_ru(r"\u041c\u043e\u0431\u0438\u043b\u044c\u043d\u044b\u0439: ") + row["mobile_phone"])
    if row.get("email"):
        lines.append(f"Email: {row['email']}")
    return "\n".join(lines)


def _render_decision_text(decision) -> str:
    header = decision.message
    if decision.results:
        body = "\n\n".join(_render_result(row, idx) for idx, row in enumerate(decision.results, start=1))
        return f"{header}\n\n{body}"
    return header


def _is_admin_access(access: AuthDecision) -> bool:
    return (access.role or "").strip().lower() in {"admin", "bypass"}


def _render_admin_only() -> str:
    return _ru(
        r"\u042d\u0442\u0430 \u043a\u043e\u043c\u0430\u043d\u0434\u0430 "
        r"\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u0430 \u0442\u043e\u043b\u044c\u043a\u043e "
        r"\u0430\u0434\u043c\u0438\u043d\u0443."
    )


def _render_manage_help() -> str:
    return _ru(
        r"\u041a\u043e\u043c\u0430\u043d\u0434\u044b "
        r"\u0443\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u044f "
        r"\u0434\u043e\u0441\u0442\u0443\u043f\u043e\u043c:\n"
        r"/whoami - \u043f\u043e\u043a\u0430\u0437\u0430\u0442\u044c \u0441\u0432\u043e\u0439 user_id \u0438 \u0440\u043e\u043b\u044c\n"
        r"/grant <user_id> [role] [display name] - \u0432\u044b\u0434\u0430\u0442\u044c \u0438\u043b\u0438 "
        r"\u043e\u0431\u043d\u043e\u0432\u0438\u0442\u044c \u0434\u043e\u0441\u0442\u0443\u043f\n"
        r"/revoke <user_id> - \u043e\u0442\u043a\u043b\u044e\u0447\u0438\u0442\u044c "
        r"\u0434\u043e\u0441\u0442\u0443\u043f\n\n"
        r"\u0420\u043e\u043b\u0438: user, admin"
    )


def _render_whoami(access: AuthDecision) -> str:
    user_id = access.external_user_id or _ru(r"\u043d\u0435 \u043e\u043f\u0440\u0435\u0434\u0435\u043b\u0451\u043d")
    role = normalize_role(access.role)
    return f"user_id: {user_id}\nrole: {role}"


def _parse_grant_command(text: str) -> tuple[str, str, str | None]:
    parts = text.split(maxsplit=3)
    if len(parts) < 2:
        raise ValueError("missing_user_id")

    user_id = parts[1].strip()
    role = "user"
    display_name = None

    if len(parts) >= 3:
        candidate_role = parts[2].strip().lower()
        if candidate_role in KNOWN_ROLES:
            role = candidate_role
            if len(parts) == 4:
                display_name = parts[3].strip() or None
        else:
            display_name = " ".join(part for part in parts[2:] if part).strip() or None

    return user_id, role, display_name


def _parse_revoke_command(text: str) -> str:
    parts = text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        raise ValueError("missing_user_id")
    return parts[1].strip()


async def _handle_management_command(event: MessageCreated, access: AuthDecision, text: str) -> bool:
    normalized_text = text.strip()
    command = normalized_text.split(maxsplit=1)[0].lower()

    if command == "/whoami":
        await event.message.answer(_render_whoami(access))
        return True

    if command in {"/grant", "/revoke", "/access"} and not _is_admin_access(access):
        await event.message.answer(_render_admin_only())
        return True

    if command == "/access":
        await event.message.answer(_render_manage_help())
        return True

    if command == "/grant":
        try:
            user_id, role, display_name = _parse_grant_command(normalized_text)
            row = grant_user_access(
                source="max",
                external_user_id=user_id,
                role=role,
                display_name=display_name,
                comment=f"Granted by MAX admin {access.external_user_id}",
            )
        except ValueError:
            await event.message.answer(
                _ru(
                    r"\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439\u0442\u0435: "
                    r"/grant <user_id> [role] [display name]"
                )
            )
            return True
        except Exception as exc:
            logger.exception("Could not grant MAX access: %r", exc)
            await event.message.answer(
                _ru(
                    r"\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c "
                    r"\u0432\u044b\u0434\u0430\u0442\u044c \u0434\u043e\u0441\u0442\u0443\u043f. "
                    r"\u041f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 user_id "
                    r"\u0438 \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u0435 \u0411\u0414."
                )
            )
            return True

        granted_display_name = row.get("display_name") or _ru(r"\u0431\u0435\u0437 \u0438\u043c\u0435\u043d\u0438")
        await event.message.answer(
            _ru(r"\u0414\u043e\u0441\u0442\u0443\u043f \u0432\u044b\u0434\u0430\u043d:\n")
            + f"user_id: {row['external_user_id']}\nrole: {normalize_role(row.get('role'))}\nname: {granted_display_name}"
        )
        return True

    if command == "/revoke":
        try:
            user_id = _parse_revoke_command(normalized_text)
            revoked = revoke_user_access(source="max", external_user_id=user_id)
        except ValueError:
            await event.message.answer(_ru(r"\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439\u0442\u0435: /revoke <user_id>"))
            return True
        except Exception as exc:
            logger.exception("Could not revoke MAX access: %r", exc)
            await event.message.answer(
                _ru(
                    r"\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c "
                    r"\u043e\u0442\u043a\u043b\u044e\u0447\u0438\u0442\u044c "
                    r"\u0434\u043e\u0441\u0442\u0443\u043f."
                )
            )
            return True

        if not revoked:
            await event.message.answer(_ru(r"\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d."))
            return True

        await event.message.answer(_ru(r"\u0414\u043e\u0441\u0442\u0443\u043f \u043e\u0442\u043a\u043b\u044e\u0447\u0451\u043d.") + f"\nuser_id: {user_id}")
        return True

    return False


def _render_auth_denied(access: AuthDecision) -> str:
    if access.reason == "missing_user_id":
        return _ru(
            r"\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c "
            r"\u043e\u043f\u0440\u0435\u0434\u0435\u043b\u0438\u0442\u044c "
            r"user id. \u041e\u0431\u0440\u0430\u0442\u0438\u0442\u0435\u0441\u044c "
            r"\u043a \u0430\u0434\u043c\u0438\u043d\u0438\u0441\u0442\u0440\u0430\u0442\u043e\u0440\u0443."
        )
    if access.reason == "auth_backend_error":
        return _ru(
            r"\u0421\u0435\u0440\u0432\u0438\u0441 "
            r"\u0430\u0432\u0442\u043e\u0440\u0438\u0437\u0430\u0446\u0438\u0438 "
            r"\u0432\u0440\u0435\u043c\u0435\u043d\u043d\u043e "
            r"\u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d. "
            r"\u041f\u043e\u0432\u0442\u043e\u0440\u0438\u0442\u0435 "
            r"\u043f\u043e\u043f\u044b\u0442\u043a\u0443 \u043f\u043e\u0437\u0436\u0435."
        )
    user_id_line = f"\n\nuser_id: {access.external_user_id}" if access.external_user_id else ""
    return (
        _ru(
            r"\u0414\u043e\u0441\u0442\u0443\u043f \u043a "
            r"\u0442\u0435\u043b\u0435\u0444\u043e\u043d\u043d\u043e\u043c\u0443 "
            r"\u0441\u043f\u0440\u0430\u0432\u043e\u0447\u043d\u0438\u043a\u0443 "
            r"\u043d\u0435 \u0432\u044b\u0434\u0430\u043d. "
            r"\u041f\u0435\u0440\u0435\u0434\u0430\u0439\u0442\u0435 "
            r"\u0430\u0434\u043c\u0438\u043d\u0438\u0441\u0442\u0440\u0430\u0442\u043e\u0440\u0443 "
            r"\u0441\u0432\u043e\u0439 user_id \u0434\u043b\u044f "
            r"\u0434\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u0438\u044f \u0432 "
            r"\u0441\u043f\u0438\u0441\u043e\u043a \u0434\u043e\u0441\u0442\u0443\u043f\u0430."
        )
        + user_id_line
    )


@dp.on_started()
async def on_started() -> None:
    logger.info("MAX bot polling started")


@dp.message_created(Command("start"))
async def handle_start(event: MessageCreated) -> None:
    access = authorize_max_event(event)
    if not access.allowed:
        await event.message.answer(_render_auth_denied(access))
        return

    text = _ru(
        r"\u041f\u0440\u0438\u0432\u0435\u0442. \u042f \u0431\u043e\u0442 "
        r"\u0442\u0435\u043b\u0435\u0444\u043e\u043d\u043d\u043e\u0433\u043e "
        r"\u0441\u043f\u0440\u0430\u0432\u043e\u0447\u043d\u0438\u043a\u0430.\n\n"
        r"\u041f\u0438\u0448\u0438 \u0437\u0430\u043f\u0440\u043e\u0441 "
        r"\u0441\u0432\u043e\u0431\u043e\u0434\u043d\u044b\u043c \u0442\u0435\u043a\u0441\u0442\u043e\u043c:\n"
        r"- \u043d\u0443\u0436\u0435\u043d \u041b\u0451\u0445\u0430 \u0438\u0437 "
        r"\u043e\u0442\u0434\u0435\u043b\u0430 \u043f\u043e\u0434\u043d\u0438\u043c\u0430\u0442\u0435\u043b\u0435\u0439 "
        r"\u043f\u0438\u043d\u0433\u0432\u0438\u043d\u043e\u0432\n"
        r"- \u043d\u0430\u0439\u0434\u0438 \u043f\u0440\u043e\u0435\u043a\u0442\u043d\u043e\u0433\u043e "
        r"\u043c\u0435\u043d\u0435\u0434\u0436\u0435\u0440\u0430 \u0418\u0432\u0430\u043d\u043e\u0432\u0430\n"
        r"- \u043a\u0442\u043e \u0443 \u043d\u0430\u0441 "
        r"\u0440\u0443\u043a\u043e\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044c "
        r"\u0418\u0422 \u0438\u043d\u0444\u0440\u0430\u0441\u0442\u0440\u0443\u043a\u0442\u0443\u0440\u044b"
    )
    if _is_admin_access(access):
        text += "\n\n" + _render_manage_help()
    await event.message.answer(text)


@dp.message_created()
async def handle_message(event: MessageCreated) -> None:
    access = authorize_max_event(event)
    if not access.allowed:
        await event.message.answer(_render_auth_denied(access))
        return

    text = (event.message.body.text or "").strip()
    if not text:
        await event.message.answer(
            _ru(
                r"\u041f\u0440\u0438\u0448\u043b\u0438 "
                r"\u0442\u0435\u043a\u0441\u0442\u043e\u0432\u044b\u0439 "
                r"\u0437\u0430\u043f\u0440\u043e\u0441. \u041d\u0430\u043f\u0440\u0438\u043c\u0435\u0440: "
                r"\u043d\u0443\u0436\u0435\u043d \u041b\u0451\u0445\u0430 \u0438\u0437 "
                r"\u0437\u0430\u043a\u0443\u043f\u043e\u043a"
            )
        )
        return

    if await _handle_management_command(event, access, text):
        return

    decision = resolve_phonebook_query(
        text,
        context=SearchContext(
            source=access.source,
            external_user_id=access.external_user_id,
            role=access.role or "user",
        ),
    )
    logger.info(
        "MAX incoming user_id=%s text=%r status=%s",
        access.external_user_id,
        text,
        decision.status,
    )
    await event.message.answer(_render_decision_text(decision))


async def run_max_bot() -> None:
    configure_logging()
    settings = get_settings()
    token = settings["max_token"].strip()
    if not token:
        raise RuntimeError("MAX_TOKEN is empty. Set it in .env before starting the bot.")

    skip_updates = settings["max_skip_updates"].lower() in {"1", "true", "yes", "y"}
    bot = Bot(token=token)
    try:
        await bot.delete_webhook()
    except Exception as exc:
        logger.warning("Could not delete webhook before polling: %r", exc)

    me = await bot.get_me()
    logger.info(
        "MAX bot authorized: id=%s name=%s",
        getattr(me, "user_id", None),
        getattr(me, "full_name", None),
    )
    await dp.start_polling(bot, skip_updates=skip_updates)


def main() -> None:
    asyncio.run(run_max_bot())


if __name__ == "__main__":
    main()
