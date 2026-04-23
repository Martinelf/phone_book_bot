from phonebook.bot import handle_user_query
from phonebook.logging_config import configure_logging


def main():
    configure_logging()
    print("Справочник сотрудников")
    print("Примеры запросов:")
    print("- 'нужен Лёха из отдела поднимателей пингвинов'")
    print("- 'найди менеджера Иванова'")
    print("- 'кто у нас руководитель ИТ инфраструктуры'")
    print("- 'exit' или 'выход' для завершения")
    print()

    while True:
        user_input = input("Введите запрос: ").strip()

        if not user_input:
            print("Запрос не может быть пустым")
            continue

        if user_input.lower() in {"exit", "quit", "q", "выход"}:
            print("Завершаю работу.")
            return

        handle_user_query(user_input)
        print("-" * 60)


if __name__ == "__main__":
    main()
