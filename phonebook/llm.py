import requests
import json

def parse_query_with_llm(user_input):
    """
    Uses a local LLM (via Ollama) to parse user input into structured data.
    """
    prompt = f"""Ты помощник для парсинга поисковых запросов в справочнике сотрудников.
Проанализируй запрос пользователя и извлеки следующую информацию в JSON:
- first_name: имя сотрудника (если есть)
- last_name: фамилия сотрудника (если есть)
- position: должность сотрудника (если есть)
- department: отдел/подразделение (если есть)

Запрос пользователя: "{user_input}"

Верни только JSON без дополнительного текста:"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "qwen3.5:2b",
            "prompt": prompt,
            "stream": True,
            "temperature": 0.1,
            "max_tokens": 256,
            "gpu_layers": 10,
            "batch_size": 64,
            "flash_attention": False
        },
        timeout=30
    )

    if response.status_code == 200:
        response_text = response.text
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            print("⚠️ Ошибка парсинга JSON. Ответ модели:", response_text)
    else:
        print("⚠️ Ошибка запроса к LLM:", response.status_code, response.text)
    return {}