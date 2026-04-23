from phonebook.llm import department_query_variants, heuristic_parse_query


def test_heuristic_parse_resolves_short_department_alias():
    parsed = heuristic_parse_query("кто из уд")

    assert parsed["department_hint"] == "отдел управления данными"


def test_heuristic_parse_resolves_single_word_department_alias():
    parsed = heuristic_parse_query("найди техподдержку")

    assert parsed["department_hint"] == "группа технической поддержки"


def test_heuristic_parse_resolves_multiword_department_alias():
    parsed = heuristic_parse_query("кто из контакт центра")

    assert parsed["department_hint"] == "центр обработки вызовов"


def test_department_query_variants_include_canonical_department():
    assert "отдел управления данными" in department_query_variants("уд")


def test_heuristic_parse_resolves_analytics_department_alias():
    parsed = heuristic_parse_query("кто из отдела аналитики")

    assert parsed["department_hint"] == "отдел информационно-аналитического обеспечения"


def test_heuristic_parse_resolves_department_head_request():
    parsed = heuristic_parse_query("кто начальник отдела аналитики")

    assert parsed["position_hint"] == "начальник"
    assert parsed["department_hint"] == "отдел информационно-аналитического обеспечения"
    assert "аналитики" not in parsed["general_terms"]
    assert "начальник" not in parsed["general_terms"]


def test_heuristic_parse_resolves_org_shortcuts():
    assert heuristic_parse_query("руководитель ркц")["department_hint"] == "региональный координационный центр"
    assert heuristic_parse_query("руководитель цит")["department_hint"] == "администрация"
    assert (
        heuristic_parse_query("руководитель центра информационных технологий")["department_hint"]
        == "администрация"
    )
