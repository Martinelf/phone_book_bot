from __future__ import annotations

import json
from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phonebook.bot import resolve_phonebook_query
from phonebook.logging_config import configure_logging

configure_logging()


def load_examples() -> list[dict]:
    eval_path = ROOT / "eval" / "phonebook_queries.jsonl"
    examples = []
    for line in eval_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            examples.append(json.loads(line))
    return examples


def result_card(row: dict) -> None:
    name = f"{row['last_name']} {row['first_name']}" + (f" {row['patronymic']}" if row.get("patronymic") else "")
    st.markdown(f"### {name}")
    st.write(f"**Должность:** {row.get('post') or '—'}")
    st.write(f"**Отдел:** {row.get('department_name') or '—'}")
    st.write(f"**Телефон:** {row.get('phone') or '—'}" + (f" доб. {row['phone_ext']}" if row.get("phone_ext") else ""))
    st.write(f"**Мобильный:** {row.get('mobile_phone') or '—'}")
    st.write(f"**Email:** {row.get('email') or '—'}")
    st.write(f"**Score:** {row.get('score')}")
    if row.get("reasons"):
        st.write("**Почему найден:** " + ", ".join(row["reasons"]))
    st.divider()


st.set_page_config(page_title="Phonebook Bot", layout="wide")
st.title("Phonebook Bot")
st.caption("Поиск сотрудника по свободному текстовому запросу")

examples = load_examples()
example_query = st.selectbox(
    "Пример запроса",
    options=[""] + [case["query"] for case in examples],
    index=0,
    help="Можно выбрать готовый пример или ввести свой текст ниже.",
)

query = st.text_area(
    "Запрос",
    value=example_query,
    height=100,
    placeholder="Например: нужен Лёха из отдела аналитики",
)

limit = st.slider("Сколько кандидатов показывать", min_value=1, max_value=10, value=3)

if st.button("Искать"):
    if not query.strip():
        st.warning("Введите запрос.")
    else:
        decision = resolve_phonebook_query(query, limit=limit)

        left, right = st.columns([1, 2])

        with left:
            st.subheader("Разбор запроса")
            st.json(decision.parsed_query)
            st.write(f"**Статус:** `{decision.status}`")
            st.write(decision.message)

        with right:
            st.subheader("Результаты")
            if not decision.results:
                st.info("Ничего не найдено.")
            else:
                for row in decision.results:
                    result_card(row)
