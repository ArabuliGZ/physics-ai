# ==========================================
# ===== РРњРџРћР Рў Р‘РР‘Р›РРћРўР•Рљ Р РњРћР”РЈР›Р•Р™ =====
# ==========================================

# Р Р°Р±РѕС‚Р° СЃ РїРµСЂРµРјРµРЅРЅС‹РјРё РѕРєСЂСѓР¶РµРЅРёСЏ
import os

# Р‘РёР±Р»РёРѕС‚РµРєР° РґР»СЏ HTTP Р·Р°РїСЂРѕСЃРѕРІ
import requests

# Р Р°Р±РѕС‚Р° СЃ JSON
import json

from dotenv import load_dotenv

load_dotenv()

from config import *

# ==================================
# ===== РћРўРљР›Р®Р§Р•РќРР• РџР РћРљРЎР =====
# ==================================

os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)

os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)


# ==========================================
# ===== РљР›Р®Р§Р РђР’РўРћР РР—РђР¦РР =====
# ==========================================

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY"
)


# ==================================
# ===== SYSTEM PROMPT Р”Р›РЇ LLM =====
# ==================================

SYSTEM_PROMPT = """
РўС‹ вЂ” СЂРµРїРµС‚РёС‚РѕСЂ РїРѕ С„РёР·РёРєРµ.

РўРІРѕСЏ Р·Р°РґР°С‡Р°:
РїРѕРјРѕРіР°С‚СЊ СѓС‡РµРЅРёРєСѓ РґСѓРјР°С‚СЊ СЃР°РјРѕСЃС‚РѕСЏС‚РµР»СЊРЅРѕ.

РўР•РљРЈР©РР™ РЈР РћР’Р•РќР¬ РџРћР”РЎРљРђР—РљР:
{hint_level}

РџР РђР’РР›Рђ:

- РќР• СЂРµС€Р°Р№ Р·Р°РґР°С‡Сѓ РїРѕР»РЅРѕСЃС‚СЊСЋ.
- РќР• РІС‹РґР°РІР°Р№ РіРѕС‚РѕРІРѕРµ СЂРµС€РµРЅРёРµ.
- РќР• СЂР°СЃРїРёСЃС‹РІР°Р№ РґР»РёРЅРЅС‹Рµ РІС‹С‡РёСЃР»РµРЅРёСЏ.
- РќР• РїРёС€Рё РґР»РёРЅРЅС‹Рµ РѕР±СЉСЏСЃРЅРµРЅРёСЏ.
- РќР• РґРµР»Р°Р№ РїРѕР»РЅС‹С… РІС‹РІРѕРґРѕРІ Р·Р° СѓС‡РµРЅРёРєР°.

РЈР РћР’РќР РџРћР”РЎРљРђР—РћРљ:

РЈСЂРѕРІРµРЅСЊ 0:
- С‚РѕР»СЊРєРѕ РєРѕСЂРѕС‚РєРёР№ РЅР°РІРѕРґСЏС‰РёР№ РІРѕРїСЂРѕСЃ
- РЅРёРєР°РєРёС… С„РѕСЂРјСѓР»
- РЅРёРєР°РєРёС… СѓРєР°Р·Р°РЅРёР№ РјРµС‚РѕРґР°

РЈСЂРѕРІРµРЅСЊ 1:
- РЅР°РјРµРє РЅР° С„РёР·РёС‡РµСЃРєСѓСЋ РёРґРµСЋ
- РјРѕР¶РЅРѕ РЅР°РїРѕРјРЅРёС‚СЊ Р·Р°РєРѕРЅ РёР»Рё РІРµР»РёС‡РёРЅСѓ

РЈСЂРѕРІРµРЅСЊ 2:
- РјРѕР¶РЅРѕ РїРѕРґСЃРєР°Р·Р°С‚СЊ СЃР»РµРґСѓСЋС‰РёР№ С€Р°Рі
- РјРѕР¶РЅРѕ РїСЂРµРґР»РѕР¶РёС‚СЊ С„РѕСЂРјСѓР»Сѓ
- РЅРѕ РЅРµ РїРѕРґСЃС‚Р°РІР»СЏС‚СЊ С‡РёСЃР»Р°

РЈСЂРѕРІРµРЅСЊ 3:
- РјРѕР¶РЅРѕ РѕРїРёСЃР°С‚СЊ РїР»Р°РЅ СЂРµС€РµРЅРёСЏ
- РЅРѕ Р±РµР· РїРѕР»РЅРѕРіРѕ СЂРµС€РµРЅРёСЏ

Р•СЃР»Рё СѓС‡РµРЅРёРє РґРІРёР¶РµС‚СЃСЏ РїСЂР°РІРёР»СЊРЅРѕ:
- РєСЂР°С‚РєРѕ РїРѕС…РІР°Р»Рё
- РїРѕРґС‚РѕР»РєРЅРё Рє СЃР»РµРґСѓСЋС‰РµРјСѓ С€Р°РіСѓ

Р•СЃР»Рё СѓС‡РµРЅРёРє РѕС€РёР±СЃСЏ:
- РѕР±СЉСЏСЃРЅРё С‚РѕР»СЊРєРѕ РєРѕРЅРєСЂРµС‚РЅСѓСЋ РѕС€РёР±РєСѓ
- РЅРµ СЂР°СЃРєСЂС‹РІР°Р№ РІСЃСЋ Р·Р°РґР°С‡Сѓ

Р”Р°Р¶Рµ РЅР° СѓСЂРѕРІРЅРµ 3:
- РќР• РІС‹РґР°РІР°Р№ РїРѕР»РЅРѕРµ СЂРµС€РµРЅРёРµ
- РќР• СЂРµС€Р°Р№ Р·Р°РґР°С‡Сѓ С†РµР»РёРєРѕРј

РћС‚РІРµС‡Р°Р№ РўРћР›Р¬РљРћ JSON.

Р¤РѕСЂРјР°С‚:

{{
  "status": "hint",
  "is_passed": false,
  "message": "РљР°РєР°СЏ СЃРёР»Р° РІС‹Р·С‹РІР°РµС‚ СѓСЃРєРѕСЂРµРЅРёРµ?"
}}

Р’РѕР·РјРѕР¶РЅС‹Рµ status:
- "hint"
- "correct"
- "error"

Field is_passed:
- true only when the student's solution is complete and correct enough to accept the task
- false when the student needs a hint, has an error, or has not completed the solution
- if status is "correct", is_passed must be true
- if status is "hint" or "error", is_passed must be false

РћРіСЂР°РЅРёС‡РµРЅРёСЏ:
- РјР°РєСЃРёРјСѓРј 2 РєРѕСЂРѕС‚РєРёС… РїСЂРµРґР»РѕР¶РµРЅРёСЏ
- РјР°РєСЃРёРјСѓРј 200 СЃРёРјРІРѕР»РѕРІ
"""


# ==================================
# ===== Р’РЎРџРћРњРћР“РђРўР•Р›Р¬РќР«Р• Р¤РЈРќРљР¦РР =====
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

    # ===== РћР‘Р«Р§РќР«Р™ TEXT MODE =====

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
                    or "РџСЂРѕР°РЅР°Р»РёР·РёСЂСѓР№ РёР·РѕР±СЂР°Р¶РµРЅРёСЏ."
            }
        ]

        # ===== РљРђР РўРРќРљРђ Р Р•РЁР•РќРРЇ =====

        if image_base64:

            content.append({

                "type": "image_url",

                "image_url": {

                    "url": image_base64
                }
            })

        # ===== РљРђР РўРРќРљРђ РЈРЎР›РћР’РРЇ =====

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
            "is_passed": False,
            "message": "РњРѕРґРµР»СЊ РЅРµ РІРµСЂРЅСѓР»Р° С‚РµРєСЃС‚"
        }

    try:

        parsed = json.loads(content)

        return normalize_llm_result(parsed)

    except Exception:

        return {
            "status": "error",
            "is_passed": False,
            "message": content
        }


def normalize_llm_result(result):
    """Normalize model JSON so progress tracking has a stable boolean."""

    if not isinstance(result, dict):

        return {
            "status": "error",
            "is_passed": False,
            "message": str(result)
        }

    status = result.get("status", "hint")
    is_passed = result.get("is_passed")

    if isinstance(is_passed, str):

        is_passed = is_passed.strip().lower() in (
            "true",
            "1",
            "yes",
            "РґР°"
        )

    if is_passed is None:

        is_passed = status == "correct"

    result["status"] = status
    result["is_passed"] = bool(is_passed)
    result["message"] = str(result.get("message", ""))

    return result

# ==========================================
# ===== РћРЎРќРћР’РќРђРЇ Р¤РЈРќРљР¦РРЇ РћР‘Р РђР©Р•РќРРЇ Рљ LLM =====
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
            "is_passed": False,
            "message": "YandexGPT РїРѕРєР° РЅРµ РїРѕРґРєР»СЋС‡РµРЅ"
        }

    elif MODEL_PROVIDER == "qwen":

        return {
            "status": "error",
            "is_passed": False,
            "message": "Qwen РїРѕРєР° РЅРµ РїРѕРґРєР»СЋС‡РµРЅ"
        }



    else:

        return {
            "status": "error",
            "is_passed": False,
            "message": "РќРµРёР·РІРµСЃС‚РЅС‹Р№ provider"
        }




# ==========================================
# ===== Р¤РЈРќРљР¦РРЇ Р—РђРџР РћРЎРђ Рљ OPENROUTER =====
# ==========================================

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
            "message": "OPENROUTER_API_KEY is not configured"
        }

    url = (
        "https://openrouter.ai/api/v1/"
        "chat/completions"
    )

    user_prompt = f"""

Р—Р°РґР°С‡Р°:
{problem_text}

Р РµС€РµРЅРёРµ СѓС‡РµРЅРёРєР°:
{solution_text}
"""

    # ===== Р”РћР‘РђР’Р›РЇР•Рњ РљРђР РўРРќРљРЈ =====

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

        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE
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
        headers=headers,
        timeout=60
    )

    print(
        "OPENROUTER STATUS:",
        response.status_code
    )

    # ===== JSON =====

    try:

        raw = response.json()

    except ValueError:

        return {

            "status": "error",
            "is_passed": False,

            "message": (
                "OpenRouter returned a non-JSON response "
                f"with status {response.status_code}"
            )
        }

    print(raw)
    
    # ===== ERROR =====

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

            error_message = str(error_value or "OpenRouter request failed")

        return {

            "status": "error",
            "is_passed": False,

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
