# ==========================================
# ===== ИМПОРТ БИБЛИОТЕК И МОДУЛЕЙ =====
# ==========================================

# Работа с переменными окружения
import os

# Библиотека для HTTP запросов
import requests

# Работа с JSON
import json

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


# ==========================================
# ===== КЛЮЧИ АВТОРИЗАЦИИ =====
# ==========================================

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
    user_prompt,
    image_base64=None,
    task_image_base64=None
):

    messages = [

        {
            "role": "system",
            "content": system_prompt
        }
    ]

    messages.extend(history)

    # ===== ОБЫЧНЫЙ TEXT MODE =====

    if (image_base64 is None and task_image_base64 is None):

        messages.append({

            "role": "user",

            "content": user_prompt
        })

    # ===== MULTIMODAL MODE =====

    else:

        content = [

            {
                "type": "text",

                "text":
                    user_prompt
                    or "Проанализируй изображения."
            }
        ]

        # ===== КАРТИНКА РЕШЕНИЯ =====

        if image_base64:

            content.append({

                "type": "image_url",

                "image_url": {

                    "url": image_base64
                }
            })

        # ===== КАРТИНКА УСЛОВИЯ =====

        if task_image_base64:

            content.append({

                "type": "image_url",

                "image_url": {

                    "url": task_image_base64
                }
            })

        messages.append({

            "role": "user",

            "content": content
        })
    return messages


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
    hint_level,
    problem_image_base64=None,
    task_image_base64=None
):

    if MODEL_PROVIDER == "openrouter":

        return ask_openrouter(
            problem_text,
            solution_text,
            history,
            hint_level,
            problem_image_base64,
            task_image_base64
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
    hint_level,
    problem_image_base64=None,
    task_image_base64=None
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

    # ===== ДОБАВЛЯЕМ КАРТИНКУ =====

    # ===== SYSTEM PROMPT =====

    system_prompt = build_system_prompt(
        hint_level
    )

    # ===== PAYLOAD =====

    payload = {

        # "model": "qwen/qwen3.7-max",
        "model": OPENROUTER_MODEL,

        "messages": build_messages(
            system_prompt,
            history,
            user_prompt,
            problem_image_base64,
            task_image_base64
        ),

        "max_tokens": MAX_TOKENS
    }

    # ===== HEADERS =====

    headers = {

        "Authorization":
            f"Bearer {OPENROUTER_API_KEY}",

        "Content-Type":
            "application/json"
    }

    # ===== REQUEST =====

    response = requests.post(
        url,
        json=payload,
        headers=headers
    )

    print(
        "OPENROUTER STATUS:",
        response.status_code
    )

    # ===== JSON =====

    raw = response.json()
    print(raw)
    
    # ===== ERROR =====

    if "choices" not in raw:

        error_message = (
            raw.get("error", {})
            .get(
                "message",
                "Ошибка OpenRouter"
            )
        )

        return {

            "status": "error",

            "message": error_message
        }

    # ===== CONTENT =====

    content = (
        raw["choices"][0]
           ["message"]
           ["content"]
    )

    # ===== PARSE =====

    return parse_json_response(
        content
    )
