import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

from config import *  # noqa: F403


# Не даём локальным proxy-переменным случайно перехватывать запросы к LLM.
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
LETOVO_LLM_API_KEY = os.getenv("LETOVO_LLM_API_KEY")


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
- намёк на физическую идею
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
  "is_passed": false,
  "message": "Какая сила вызывает ускорение?"
}}

Возможные status:
- "hint"
- "correct"
- "error"

Поле is_passed:
- true только если решение ученика достаточно полное и правильное, чтобы зачесть задачу
- false если ученику нужна подсказка, в решении есть ошибка или решение не завершено
- если status равен "correct", is_passed должен быть true
- если status равен "hint" или "error", is_passed должен быть false

Ограничения:
- максимум 2 коротких предложения
- максимум 200 символов
"""


def build_system_prompt(hint_level):
    return SYSTEM_PROMPT.format(hint_level=hint_level)


def build_attachment_part(data_url):
    """Build an OpenAI-compatible image content part."""

    return {
        "type": "image_url",
        "image_url": {
            "url": data_url,
        },
    }


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
            "content": system_prompt,
        }
    ]

    messages.extend(history)

    if image_base64 is None and task_image_base64 is None:
        messages.append(
            {
                "role": "user",
                "content": user_prompt,
            }
        )
        return messages

    content = [
        {
            "type": "text",
            "text": user_prompt or "Проанализируй изображения.",
        }
    ]

    if image_base64:
        content.append(build_attachment_part(image_base64))

    if task_image_base64:
        content.append(build_attachment_part(task_image_base64))

    messages.append(
        {
            "role": "user",
            "content": content,
        }
    )
    return messages


def clean_json_response(content):
    if content is None:
        return None

    content = content.replace("```json", "")
    content = content.replace("```", "")
    return content.strip()


def parse_json_response(content):
    content = clean_json_response(content)

    if content is None:
        return {
            "status": "error",
            "is_passed": False,
            "message": "Модель не вернула текст",
        }

    try:
        parsed = json.loads(content)
        return normalize_llm_result(parsed)
    except Exception:
        return {
            "status": "error",
            "is_passed": False,
            "message": content,
        }


def normalize_llm_result(result):
    """Normalize model JSON so progress tracking has a stable boolean."""

    if not isinstance(result, dict):
        return {
            "status": "error",
            "is_passed": False,
            "message": str(result),
        }

    status = result.get("status", "hint")
    is_passed = result.get("is_passed")

    if isinstance(is_passed, str):
        is_passed = is_passed.strip().lower() in (
            "true",
            "1",
            "yes",
            "да",
        )

    if is_passed is None:
        is_passed = status == "correct"

    result["status"] = status
    result["is_passed"] = bool(is_passed)
    result["message"] = str(result.get("message", ""))
    return result


def ask_llm(
    problem_text,
    solution_text,
    history,
    hint_level,
    problem_image_base64=None,
    task_image_base64=None
):
    if MODEL_PROVIDER == "letovo":  # noqa: F405
        return ask_letovo_llm(
            problem_text,
            solution_text,
            history,
            hint_level,
            problem_image_base64,
            task_image_base64,
        )

    if MODEL_PROVIDER == "openrouter":  # noqa: F405
        return ask_openrouter(
            problem_text,
            solution_text,
            history,
            hint_level,
            problem_image_base64,
            task_image_base64,
        )

    if MODEL_PROVIDER == "yandex":  # noqa: F405
        return {
            "status": "error",
            "is_passed": False,
            "message": "YandexGPT пока не подключён",
        }

    if MODEL_PROVIDER == "qwen":  # noqa: F405
        return {
            "status": "error",
            "is_passed": False,
            "message": "Qwen пока не подключён",
        }

    return {
        "status": "error",
        "is_passed": False,
        "message": "Неизвестный provider",
    }


def build_check_payload(
    model,
    problem_text,
    solution_text,
    history,
    hint_level,
    problem_image_base64=None,
    task_image_base64=None,
    response_format=None
):
    user_prompt = f"""
Задача:
{problem_text}

Решение ученика:
{solution_text}
"""

    payload = {
        "model": model,
        "messages": build_messages(
            build_system_prompt(hint_level),
            history,
            user_prompt,
            problem_image_base64,
            task_image_base64,
        ),
        "max_tokens": MAX_TOKENS,  # noqa: F405
        "temperature": TEMPERATURE,  # noqa: F405
    }

    if response_format is not None:
        payload["response_format"] = response_format

    return payload


def send_openai_compatible_request(url, payload, headers, provider_name):
    request_headers = {
        "Content-Type": "application/json",
        **headers,
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers=request_headers,
            timeout=LLM_REQUEST_TIMEOUT,  # noqa: F405
        )
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "is_passed": False,
            "message": (
                "Модель слишком долго отвечает. "
                "Попробуй отправить изображение меньшего размера или повторить позже."
            ),
        }
    except requests.exceptions.RequestException as error:
        return {
            "status": "error",
            "is_passed": False,
            "message": f"Не удалось подключиться к LLM: {error}",
        }

    print(f"{provider_name.upper()} STATUS:", response.status_code)

    try:
        raw = response.json()
    except ValueError:
        return {
            "status": "error",
            "is_passed": False,
            "message": (
                f"{provider_name} returned a non-JSON response "
                f"with status {response.status_code}"
            ),
        }

    print(raw)

    if response.status_code >= 400 or "choices" not in raw:
        error_value = raw.get("error") if isinstance(raw, dict) else raw

        if isinstance(error_value, dict):
            error_message = (
                error_value.get("message")
                or error_value.get("error")
                or str(error_value)
            )
        elif isinstance(error_value, str):
            error_message = error_value
        else:
            error_message = str(error_value or f"{provider_name} request failed")

        return {
            "status": "error",
            "is_passed": False,
            "message": error_message,
        }

    content = raw["choices"][0]["message"]["content"]
    return parse_json_response(content)


def ask_letovo_llm(
    problem_text,
    solution_text,
    history,
    hint_level,
    problem_image_base64=None,
    task_image_base64=None
):
    if not LETOVO_LLM_API_KEY:
        return {
            "status": "error",
            "is_passed": False,
            "message": "LETOVO_LLM_API_KEY is not configured",
        }

    payload = build_check_payload(
        LETOVO_LLM_MODEL,  # noqa: F405
        problem_text,
        solution_text,
        history,
        hint_level,
        problem_image_base64,
        task_image_base64,
        response_format={"type": "json_object"},
    )

    return send_openai_compatible_request(
        LETOVO_LLM_API_URL,  # noqa: F405
        payload,
        {
            "Authorization": f"Bearer {LETOVO_LLM_API_KEY}",
        },
        "letovo",
    )


def ask_openrouter(
    problem_text,
    solution_text,
    history,
    hint_level,
    problem_image_base64=None,
    task_image_base64=None
):
    if not OPENROUTER_API_KEY:
        return {
            "status": "error",
            "is_passed": False,
            "message": "OPENROUTER_API_KEY is not configured",
        }

    payload = build_check_payload(
        OPENROUTER_MODEL,  # noqa: F405
        problem_text,
        solution_text,
        history,
        hint_level,
        problem_image_base64,
        task_image_base64,
    )

    return send_openai_compatible_request(
        "https://openrouter.ai/api/v1/chat/completions",
        payload,
        {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://test.physais.ru",
            "X-OpenRouter-Title": "Physics AI",
        },
        "openrouter",
    )
