from phonebook.bot import handle_user_query

def main():
    print("🔍 Справочник сотрудников")
    print("Примеры запросов:")
    print("- 'нужен сисадмин артём'")
    print("- 'найти менеджера Иванова'")
    print("- 'директор отдела IT'")
    print()

    user_input = input("Введите запрос: ").strip()

    if not user_input:
        print("Запрос не может быть пустым")
        return

    handle_user_query(user_input)

if __name__ == "__main__":
    main()