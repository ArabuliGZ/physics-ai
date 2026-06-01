# ==========================================
# ===== ИМПОРТ БИБЛИОТЕК И МОДУЛЕЙ =====
# ==========================================

# Работа с переменными окружения
import os

# Библиотека для HTTP запросов
import requests

# Нужна для генерации уникального ID
import uuid

# Работа с JSON
import json

# Библиотека для управления HTTPS warning
import urllib3

from dotenv import load_dotenv

load_dotenv()

from config import *

# ==================================
# ===== ОТКЛЮЧЕНИЕ ПРОКСИ =====
# ==================================

os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)

os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)


# ==================================================
# ===== ОТКЛЮЧЕНИЕ WARNING ДЛЯ verify=False =====
# ==================================================

urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)

# ==========================================
# ===== КЛЮЧИ АВТОРИЗАЦИИ =====
# ==========================================

GIGACHAT_AUTH_KEY = os.getenv(
    "GIGACHAT_AUTH_KEY"
)

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY"
)


# ==================================
# ===== SYSTEM PROMPT ДЛЯ LLM =====
# ==================================

SYSTEM_PROMPT = """
Ты — репетитор по физике.

Твоя задача:
помогать ученику думать самостоятельно.

ТЕКУЩИЙ УРОВЕНЬ ПОДСКАЗКИ:
{hint_level}

ПРАВИЛА:

- НЕ решай задачу полностью.
- НЕ выдавай готовое решение.
- НЕ расписывай длинные вычисления.
- НЕ пиши длинные объяснения.
- НЕ делай полных выводов за ученика.

УРОВНИ ПОДСКАЗОК:

Уровень 0:
- только короткий наводящий вопрос
- никаких формул
- никаких указаний метода

Уровень 1:
- намек на физическую идею
- можно напомнить закон или величину

Уровень 2:
- можно подсказать следующий шаг
- можно предложить формулу
- но не подставлять числа

Уровень 3:
- можно описать план решения
- но без полного решения

Если ученик движется правильно:
- кратко похвали
- подтолкни к следующему шагу

Если ученик ошибся:
- объясни только конкретную ошибку
- не раскрывай всю задачу

Даже на уровне 3:
- НЕ выдавай полное решение
- НЕ решай задачу целиком

Отвечай ТОЛЬКО JSON.

Формат:

{{
  "status": "hint",
  "message": "Какая сила вызывает ускорение?"
}}

Возможные status:
- "hint"
- "correct"
- "error"

Ограничения:
- максимум 2 коротких предложения
- максимум 200 символов
"""


# ==================================
# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
# ==================================

def build_system_prompt(hint_level):

    return SYSTEM_PROMPT.format(
        hint_level=hint_level
    )


def build_messages(
    system_prompt,
    history,
    user_prompt
):

    return [

        {
            "role": "system",
            "content": system_prompt
        },

        *history,

        {
            "role": "user",
            "content": user_prompt
        }
    ]


def clean_json_response(content):

    if content is None:

        return None

    content = content.replace(
        "```json",
        ""
    )

    content = content.replace(
        "```",
        ""
    )

    return content.strip()

def parse_json_response(content):

    content = clean_json_response(
        content
    )

    if content is None:

        return {
            "status": "error",
            "message": "Модель не вернула текст"
        }

    try:

        return json.loads(content)

    except Exception:

        return {
            "status": "error",
            "message": content
        }

# ==========================================
# ===== ОСНОВНАЯ ФУНКЦИЯ ОБРАЩЕНИЯ К LLM =====
# ==========================================

def ask_llm(
    problem_text,
    solution_text,
    history,
    hint_level
):

    if MODEL_PROVIDER == "gigachat":

        return ask_gigachat(
            problem_text,
            solution_text,
            history,
            hint_level
        )

    elif MODEL_PROVIDER == "yandex":

        return {
            "status": "error",
            "message": "YandexGPT пока не подключен"
        }

    elif MODEL_PROVIDER == "qwen":

        return {
            "status": "error",
            "message": "Qwen пока не подключен"
        }

    elif MODEL_PROVIDER == "openrouter":

        return ask_openrouter(
            problem_text,
            solution_text,
            history,
            hint_level
        )

    else:

        return {
            "status": "error",
            "message": "Неизвестный provider"
        }




# ==========================================
# ===== ФУНКЦИЯ ЗАПРОСА К OPENROUTER =====
# ==========================================

def ask_openrouter(
    problem_text,
    solution_text,
    history,
    hint_level
):

    url = (
        "https://openrouter.ai/api/v1/"
        "chat/completions"
    )

    user_prompt = f"""
Задача:
{problem_text}

Решение ученика:
{solution_text}
"""

    system_prompt = build_system_prompt(
        hint_level
    )

    payload = {

        # "model": "qwen/qwen3.7-max",
        "model": OPENROUTER_MODEL,

        "messages": build_messages(
            system_prompt,
            history,
            user_prompt
        ),

        "max_tokens": MAX_TOKENS
    }

    headers = {

        "Authorization":
            f"Bearer {OPENROUTER_API_KEY}",

        "Content-Type":
            "application/json"
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers
    )

    print(
        "OPENROUTER STATUS:",
        response.status_code
    )

    raw = response.json()

    if "choices" not in raw:

        error_message = (
            raw.get("error", {})
            .get("message",
                    "Ошибка OpenRouter")
        )

        return {
            "status": "error",
            "message": error_message
        }

    content = (
        raw["choices"][0]
           ["message"]
           ["content"]
    )

    return parse_json_response(
            content
        )


# ==========================================
# ===== ФУНКЦИЯ ЗАПРОСА К GIGACHAT =====
# ==========================================

def ask_gigachat(
    problem_text,
    solution_text,
    history,
    hint_level
):

    # ==================================
    # ===== ПОЛУЧЕНИЕ ACCESS TOKEN =====
    # ==================================

    auth_url = (
        "https://ngw.devices.sberbank.ru:9443/"
        "api/v2/oauth"
    )

    auth_payload = {
        "scope": "GIGACHAT_API_PERS"
    }

    auth_headers = {

        "Content-Type":
            "application/x-www-form-urlencoded",

        "Accept":
            "application/json",

        "RqUID":
            str(uuid.uuid4()),

        "Authorization":
            f"Basic {GIGACHAT_AUTH_KEY}"
    }

    response = requests.post(

        auth_url,

        headers=auth_headers,

        data=auth_payload,

        verify=False,

        proxies={}
    )

    print(
        "AUTH STATUS:",
        response.status_code
    )

    auth_data = response.json()

    access_token = auth_data["access_token"]


    # ==================================
    # ===== ЗАПРОС К МОДЕЛИ =====
    # ==================================

    chat_url = (
        "https://gigachat.devices.sberbank.ru/"
        "api/v1/chat/completions"
    )

    user_prompt = f"""
Задача:
{problem_text}

Решение ученика:
{solution_text}
"""

    system_prompt = build_system_prompt(
        hint_level
    )

    chat_payload = {

        "model": GIGACHAT_MODEL,

        "messages": build_messages(
            system_prompt,
            history,
            user_prompt
        ),

        "temperature": TEMPERATURE
    }

    chat_headers = {

        "Authorization":
            f"Bearer {access_token}",

        "Content-Type":
            "application/json"
    }

    print("\n===== MESSAGES =====")

    for msg in chat_payload["messages"]:

        print("\nROLE:", msg["role"])
        print(msg["content"])

    print("\n====================\n")

    chat_response = requests.post(

        chat_url,

        json=chat_payload,

        headers=chat_headers,

        proxies={}
    )

    print(
        "CHAT STATUS:",
        chat_response.status_code
    )

    print(chat_response.text)

    raw = chat_response.json()

    content = (
        raw["choices"][0]
           ["message"]
           ["content"]
    )

    return parse_json_response(
        content
    )

