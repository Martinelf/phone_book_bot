from phonebook.llm import heuristic_parse_query, query_token_variants


def test_heuristic_parse_extracts_name_and_department():
    parsed = heuristic_parse_query("Нужен Лёха из отдела поднимателей пингвинов")

    assert parsed["first_name"] == "алексей"
    assert parsed["department_hint"] == "пингвины"


def test_heuristic_parse_normalizes_last_name_case():
    parsed = heuristic_parse_query("Найди Иванову")

    assert parsed["last_name"] == "иванова"


def test_heuristic_parse_ignores_service_words_around_last_name():
    parsed = heuristic_parse_query("Дай контакт Иванова, в каком отделе работает")

    assert parsed["last_name"] == "иванова"
    assert "контакт" not in parsed["general_terms"]
    assert "каком" not in parsed["general_terms"]
    assert "отделе" not in parsed["general_terms"]
    assert "работает" not in parsed["general_terms"]


def test_query_token_variants_supports_case_forms_and_easter_egg():
    assert "аленид" in query_token_variants("Аленида")
    assert "игорь" in query_token_variants("Игоря")
    assert "аленид" in query_token_variants("Тони")
    assert "никита" in query_token_variants("Никиты")
    assert "сергей" in query_token_variants("Сергея")
    assert "роман" in query_token_variants("Романа")
    assert "мария" in query_token_variants("Марии")
    assert "саня" in query_token_variants("Сани")
    assert "настя" in query_token_variants("Насти")


def test_heuristic_parse_does_not_duplicate_normalized_last_name_in_general_terms():
    parsed = heuristic_parse_query("В каком отделе Иванова")

    assert parsed["last_name"] == "иванова"
    assert "иванов" not in parsed["general_terms"]


def test_query_token_variants_supports_patronymic_and_adjective_endings():
    assert "эдуардович" in query_token_variants("Эдуардовича")
    assert "петровский" in query_token_variants("Петровского")
    assert "толстой" in query_token_variants("Толстого")
    assert "белая" in query_token_variants("Белой")


def test_heuristic_parse_extracts_adjective_last_names():
    parsed = heuristic_parse_query("Дай номер Толстого")
    assert parsed["last_name"] == "толстой"

    parsed_feminine = heuristic_parse_query("Контакт Белой")
    assert parsed_feminine["last_name"] in {"белой", "белая"}


def test_heuristic_parse_normalizes_feminine_last_names_with_oy_endings():
    assert heuristic_parse_query("телефон Ивановой")["last_name"] == "иванова"
    assert heuristic_parse_query("телефон Данилиной")["last_name"] == "данилина"
    assert heuristic_parse_query("телефон Сергеевой")["last_name"] == "сергеева"


def test_heuristic_parse_supports_inflected_informal_names():
    assert heuristic_parse_query("дай номер Сани")["first_name"] == "александр"
    assert heuristic_parse_query("в каком отделе Насти")["first_name"] == "анастасия"
    assert heuristic_parse_query("телефон Никиты")["first_name"] == "никита"
    assert heuristic_parse_query("контакт Сергея")["first_name"] == "сергей"
