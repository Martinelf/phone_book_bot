# Install

## Локальный запуск

### 1. Создать окружение

```bash
conda create -n phonebook-bot python=3.11 -y
conda activate phonebook-bot
cd D:\DS\phone_book_bot-main
pip install -r requirements.txt
```

### 2. Создать `.env`

```bash
copy .env.example .env
```

Минимально проверь:

```env
PG_HOST=localhost
PG_PORT=5432
PG_DB=phone_book_demo
PG_ADMIN_DB=postgres
PG_USER=postgres
PG_PASSWORD=1234
PG_SCHEMA=bot_test
MAX_TOKEN=твой_токен_бота
MAX_SKIP_UPDATES=true
LOG_LEVEL=INFO
LOG_FILE=logs/phonebook.log
```

### 3. Поднять синтетическую БД

```bash
python scripts\init_synthetic_db.py
```

### 4. Запустить MAX-бота

```bash
python scripts\run_max_bot.py
```

### 5. Дополнительные режимы

CLI:

```bash
python main.py
```

Streamlit:

```bash
python -m streamlit run apps\streamlit_app.py
```

Eval:

```bash
python scripts\run_eval.py
```

Tests:

```bash
pytest
```

## Docker

### 1. Заполни `.env`

Особенно:

- `PG_PASSWORD`
- `MAX_TOKEN`

### 2. Подними сервисы

```bash
docker compose up --build
```

### 3. Что внутри

- `postgres` создаёт БД и применяет [sql/synthetic_phonebook.sql](D:/DS/phone_book_bot-main/sql/synthetic_phonebook.sql:1)
- `max-bot` запускает [phonebook/max_bot.py](D:/DS/phone_book_bot-main/phonebook/max_bot.py:1)

### 4. Остановить

```bash
docker compose down
```

Если нужен чистый сброс данных:

```bash
docker compose down -v
```

## Ollama

Оционально. Бот работает и без неё.

```bash
ollama pull qwen3.5:2b
ollama serve
```

Если Ollama недоступна, проект переключается на heuristic fallback.
