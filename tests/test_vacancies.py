from phonebook.bot import _is_vacancy_row


def test_is_vacancy_row_detects_vacancy_placeholder():
    row = {
        "last_name": "ВАКАНСИЯ",
        "first_name": "",
        "patronymic": None,
    }

    assert _is_vacancy_row(row) is True
