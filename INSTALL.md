# Install

Актуальная инструкция по запуску находится в `readme.md`.

Короткая версия:

## Локальный запуск

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Дальше:

1. настрой `.env`
2. подготовь PostgreSQL
3. при необходимости добавь `sql/synthetic_phonebook.sql` или адаптируй скрипты под свою схему
4. запускай нужный режим:

```powershell
python main.py
python scripts\run_max_bot.py
python -m streamlit run apps\streamlit_app.py
python scripts\run_eval.py
pytest
```

## Docker

```powershell
docker compose up --build
```

Важно: `docker-compose.yml` сейчас ожидает файл `sql/synthetic_phonebook.sql`. Если его нет, Docker-сценарий нужно дополнить этим файлом или изменить инициализацию БД.
