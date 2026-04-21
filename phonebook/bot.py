from phonebook.db import execute_query
from phonebook.llm import parse_query_with_llm

def build_search_query(parsed_data, user_input):
    """
    Builds an SQL query based on parsed LLM data.
    """
    conditions = ["is_active = true"]
    params = []

    if parsed_data:
        if parsed_data.get("last_name"):
            conditions.append("last_name ILIKE %s")
            params.append(f"%{parsed_data['last_name']}%")

        if parsed_data.get("first_name"):
            conditions.append("first_name ILIKE %s")
            params.append(f"%{parsed_data['first_name']}%")

        if parsed_data.get("position"):
            conditions.append("post ILIKE %s")
            params.append(f"%{parsed_data['position']}%")

        if parsed_data.get("department"):
            conditions.append("department_id = %s")
            params.append(parsed_data['department'])

    if not params:
        conditions.append("(last_name ILIKE %s OR first_name ILIKE %s OR post ILIKE %s)")
        params = [f"%{user_input}%", f"%{user_input}%", f"%{user_input}%"]

    where_clause = " AND ".join(conditions)
    return f"""
        SELECT id_phone_directory, last_name, first_name, patronymic, phone, mobile_phone, post, department_id
        FROM phone_directory
        WHERE {where_clause}
    """, params

def handle_user_query(user_input):
    """
    Handles the user query by parsing it with LLM and querying the database.
    """
    print("\n⏳ Обработка запроса...")
    parsed_data = parse_query_with_llm(user_input)
    print(f"📊 Распарсено: {parsed_data}")

    query, params = build_search_query(parsed_data, user_input)
    rows = execute_query(query, params)

    if rows:
        print(f"\n✅ Найдено: {len(rows)} результат(ов)\n")
        for row in rows:
            last_name, first_name, patronymic, phone, mobile_phone, post = row[1], row[2], row[3], row[4], row[5], row[6]
            full_name = f"{last_name} {first_name}"
            if patronymic:
                full_name += f" {patronymic}"

            print(f"{full_name}")
            if post:
                print(f"  💼 Должность: {post}")
            if phone:
                print(f"  📞 Телефон: {phone}")
            if mobile_phone:
                print(f"  📱 Мобильный: {mobile_phone}")
            print()
    else:
        print("❌ Ничего не найдено")