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
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")


def get_env_bool(name, default):
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
        "да",
    )


SYSTEM_PROMPT = """
Ты — дружелюбный помощник по физике для школьника.

Твоя задача — помочь ученику понять, верно ли он решает задачу, и мягко подсказать, что исправить.

Это не контрольная и не экзамен. За ответ ученику не ставится оценка. Не заваливай ученика и не придирайся к оформлению, если физическая идея и ход решения верные.

Правила:
- Отвечай доброжелательно и коротко.
- Если решение верное или почти верное, скажи это явно.
- Если есть ошибка, укажи конкретное место ошибки и предложи следующий шаг.
- Не ругай ученика и не обесценивай его попытку.
- Не требуй идеального оформления.
- Не выдавай полное решение сразу, если ученик еще может сам дойти.
- Не расписывай длинные вычисления.
- Если ученик прислал только ответ, проверь его по возможности и попроси ход решения, если без него нельзя уверенно зачесть.
- Если не хватает данных или изображение не читается, скажи об этом прямо и попроси уточнение.

Как решать, зачтено или нет:
- Ставь is_passed=true, если ответ физически верный и решение достаточно убедительное.
- Допускай эквивалентные формулы, разумные округления и другой порядок рассуждений.
- Не снимай зачет за мелкие ошибки оформления, если смысл правильный.
- Ставь is_passed=false, если есть существенная физическая ошибка, неверный ответ или решение невозможно проверить.

Поле status — это только итог проверки:
- "correct", если задача решена и is_passed=true.
- "error", если задача не решена и is_passed=false.

Тон ответа:
- Пиши спокойно и по делу, без восторженного тона.
- Не используй восклицательные знаки.

Отвечай ТОЛЬКО JSON.

Формат:

{{
  "status": "error",
  "is_passed": false,
  "message": "Короткий дружелюбный ответ ученику"
}}

Ограничения:
- message: максимум 2-3 коротких предложения.
- Не используй markdown-таблицы.
- Не пиши полный разбор задачи, если ученик не попросил.
"""


def build_system_prompt(hint_level, reference_answer=None):
    prompt = SYSTEM_PROMPT.format(hint_level=hint_level)

    if reference_answer is None or not str(reference_answer).strip():
        return prompt

    return (
        prompt
        + "\n\n"
        + "Эталонный ответ из базы:\n"
        + str(reference_answer).strip()
        + "\n\n"
        + "Используй эталон только для внутренней проверки решения. "
        + "Не раскрывай его ученику напрямую, пока ученик сам не получил "
        + "ответ или явно не попросил полное решение. Учитывай эквивалентные "
        + "формы записи, допустимые округления и возможную опечатку в эталоне."
    )


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

    status = result.get("status", "error")
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

    is_passed = bool(is_passed)
    result["status"] = "correct" if is_passed else "error"
    result["is_passed"] = is_passed
    result["message"] = str(result.get("message", ""))
    return result


def ask_llm(
    problem_text,
    solution_text,
    history,
    hint_level,
    problem_image_base64=None,
    task_image_base64=None,
    reference_answer=None,
):
    if MODEL_PROVIDER == "letovo":  # noqa: F405
        return ask_letovo_llm(
            problem_text,
            solution_text,
            history,
            hint_level,
            problem_image_base64,
            task_image_base64,
            reference_answer,
        )

    if MODEL_PROVIDER == "openrouter":  # noqa: F405
        return ask_openrouter(
            problem_text,
            solution_text,
            history,
            hint_level,
            problem_image_base64,
            task_image_base64,
            reference_answer,
        )

    if MODEL_PROVIDER in ("qwencloud", "qwen"):  # noqa: F405
        return ask_qwencloud(
            problem_text,
            solution_text,
            history,
            hint_level,
            problem_image_base64,
            task_image_base64,
            reference_answer,
        )

    if MODEL_PROVIDER == "yandex":  # noqa: F405
        return {
            "status": "error",
            "is_passed": False,
            "message": "YandexGPT пока не подключён",
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
    response_format=None,
    reference_answer=None,
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
            build_system_prompt(hint_level, reference_answer),
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
    task_image_base64=None,
    reference_answer=None,
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
        reference_answer=reference_answer,
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
    task_image_base64=None,
    reference_answer=None,
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
        reference_answer=reference_answer,
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


def ask_qwencloud(
    problem_text,
    solution_text,
    history,
    hint_level,
    problem_image_base64=None,
    task_image_base64=None,
    reference_answer=None,
):
    if not DASHSCOPE_API_KEY:
        return {
            "status": "error",
            "is_passed": False,
            "message": "DASHSCOPE_API_KEY is not configured",
        }

    qwen_model = os.getenv("QWEN_CLOUD_MODEL", QWEN_CLOUD_MODEL)  # noqa: F405
    qwen_api_url = os.getenv(
        "QWEN_CLOUD_LLM_API_URL",
        QWEN_CLOUD_LLM_API_URL,  # noqa: F405
    )
    qwen_enable_thinking = get_env_bool(
        "QWEN_CLOUD_ENABLE_THINKING",
        QWEN_CLOUD_ENABLE_THINKING,  # noqa: F405
    )

    payload = build_check_payload(
        qwen_model,
        problem_text,
        solution_text,
        history,
        hint_level,
        problem_image_base64,
        task_image_base64,
        reference_answer=reference_answer,
    )

    if qwen_enable_thinking:
        payload["enable_thinking"] = True

    return send_openai_compatible_request(
        qwen_api_url,
        payload,
        {
            "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
        },
        "qwencloud",
    )
