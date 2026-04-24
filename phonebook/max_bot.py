from __future__ import annotations

import asyncio
import logging

from maxapi import Bot, Dispatcher
from maxapi.types import Command, MessageCreated

from phonebook.auth import AuthDecision, authorize_max_event
from phonebook.bot import resolve_phonebook_query
from phonebook.config import get_settings
from phonebook.logging_config import configure_logging

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

    decision = resolve_phonebook_query(text)
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
