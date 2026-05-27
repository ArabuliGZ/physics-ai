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
# ==================================
# ===== ОТКЛЮЧЕНИЕ ПРОКСИ =====
# ==================================

# Иногда Windows или IDE автоматически
# подставляют прокси.
# Это может ломать запросы к GigaChat.

os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)

os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)


# ==================================================
# ===== ОТКЛЮЧЕНИЕ WARNING ДЛЯ verify=False =====
# ==================================================

# verify=False отключает проверку SSL сертификата.
# Python начинает спамить warning.
# Мы их отключаем.

urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)


# ==================================
# ===== ВЫБОР LLM ПРОВАЙДЕРА =====
# ==================================

# Какую модель использовать
MODEL_PROVIDER = "gigachat"


# ==========================================
# ===== КЛЮЧ АВТОРИЗАЦИИ GIGACHAT =====
# ==========================================

# Base64 ключ из личного кабинета Сбера
GIGACHAT_AUTH_KEY = os.getenv(
    "GIGACHAT_AUTH_KEY"
)


# ==================================
# ===== SYSTEM PROMPT ДЛЯ LLM =====
# ==================================

# Это главный системный промпт.
# Он определяет поведение модели.

SYSTEM_PROMPT = r"""
Ты — помощник по физике.

Всегда сначала самостоятельно решай задачу внутренне, но НЕ показывай внутренние рассуждения.

Если ученик просто прислал задачу:
- дай только краткое решение,
- без объяснений,
- без подробного вывода формул,
- без рассуждений.

Подробное решение разрешено ТОЛЬКО если ученик явно попросил:
- "объясни",
- "подробно",
- "покажи решение",
- "не понял".

Во всех остальных случаях отвечай строго в формате JSON:

{
  "status": "solution",
  "message": "..."
}

Правила для поля "message":
- только LaTeX,
- использовать только одинарные $...$,
- не использовать $$,
- каждая формула с новой строки,
- не использовать списки,
- не писать обычный текст вне $...$,
- не писать слова:
  - "где"
  - "подставим"
  - "решаем"
  - "следовательно"
  - "ответ"
  - "получаем"
- максимум 6 строк,
- максимум 600 символов,
- последняя строка должна содержать ответ в формате $\boxed{...}$.

Запрещено:
- добавлять пояснения,
- пересказывать условие,
- использовать markdown кроме JSON,
- писать текст до или после JSON,
- добавлять комментарии.

Если задача не распознана:
{
  "status": "error",
  "message": "Не удалось распознать условие задачи."
}

Если данных недостаточно:
{
  "status": "error",
  "message": "Недостаточно данных для решения."
}
"""

# ==========================================
# ===== ОСНОВНАЯ ФУНКЦИЯ ОБРАЩЕНИЯ К LLM =====
# ==========================================

def ask_llm(
    problem_text,
    solution_text,
    history
):

    # Если выбран GigaChat
    if MODEL_PROVIDER == "gigachat":

        return ask_gigachat(
            problem_text,
            solution_text,
            history
        )

    # Заглушка для YandexGPT
    elif MODEL_PROVIDER == "yandex":

        return {
            "status": "error",
            "message": "YandexGPT пока не подключен"
        }

    # Заглушка для Qwen
    elif MODEL_PROVIDER == "qwen":

        return {
            "status": "error",
            "message": "Qwen пока не подключен"
        }

    # Если provider неизвестен
    else:

        return {
            "status": "error",
            "message": "Неизвестный provider"
        }


# ==========================================
# ===== ФУНКЦИЯ ЗАПРОСА К GIGACHAT =====
# ==========================================

def ask_gigachat(
    problem_text,
    solution_text,
    history
):

    # ==================================
    # ===== ПОЛУЧЕНИЕ ACCESS TOKEN =====
    # ==================================

    # URL авторизации
    auth_url = (
        "https://ngw.devices.sberbank.ru:9443/"
        "api/v2/oauth"
    )

    # Что запрашиваем
    auth_payload = {
        "scope": "GIGACHAT_API_PERS"
    }

    # Заголовки авторизации
    auth_headers = {

        # Тип данных
        "Content-Type":
            "application/x-www-form-urlencoded",

        # Хотим получить JSON
        "Accept":
            "application/json",

        # Уникальный ID запроса
        "RqUID":
            str(uuid.uuid4()),

        # Basic авторизация
        "Authorization":
            f"Basic {GIGACHAT_AUTH_KEY}"
    }

    # Отправляем POST запрос
    response = requests.post(

        # URL
        auth_url,

        # Заголовки
        headers=auth_headers,

        # Данные
        data=auth_payload,

        # Отключаем SSL проверку
        verify=False,

        # Отключаем прокси
        proxies={}
    )

    # Выводим статус для отладки
    print("AUTH STATUS:", response.status_code)

    # Выводим ответ сервера
    print(response.text)

    # Преобразуем ответ в JSON
    auth_data = response.json()

    # Достаем access token
    access_token = auth_data["access_token"]


    # ==================================
    # ===== ЗАПРОС К МОДЕЛИ =====
    # ==================================

    # URL chat API
    chat_url = (
        "https://gigachat.devices.sberbank.ru/"
        "api/v1/chat/completions"
    )

    # Формируем prompt для пользователя
    user_prompt = f"""
Задача:
{problem_text}

Решение ученика:
{solution_text}
"""

    # Тело запроса
    chat_payload = {

        # Какая модель используется
        "model": "GigaChat",

        # История сообщений
        "messages": [

            # SYSTEM PROMPT
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            
            *history,

            # Сообщение пользователя
            {
                "role": "user",
                "content": user_prompt
            }
        ],

        # Температура:
        # маленькая = более стабильные ответы
        "temperature": 0.2
    }

    # Заголовки запроса
    chat_headers = {

        # Bearer токен авторизации
        "Authorization":
            f"Bearer {access_token}",

        # Отправляем JSON
        "Content-Type":
            "application/json"
    }

    #####TEST
    print("\n===== MESSAGES =====")

    for msg in chat_payload["messages"]:

        print("\nROLE:", msg["role"])
        print(msg["content"])

    print("\n====================\n")
 #####TEST


    # Отправляем запрос к модели
    chat_response = requests.post(

        # URL API
        chat_url,

        # JSON тело
        json=chat_payload,

        # Заголовки
        headers=chat_headers,

        # SSL off
        verify=False,

        # Без прокси
        proxies={}
    )

    # Статус ответа
    print("CHAT STATUS:", chat_response.status_code)

    # Полный ответ сервера
    print(chat_response.text)

    # Переводим ответ в JSON
    raw = chat_response.json()

    # Достаем текст ответа модели
    content = (
        raw["choices"][0]
           ["message"]
           ["content"]
    )

    # ==================================
    # ===== ПАРСИНГ JSON ОТ МОДЕЛИ =====
    # ==================================

    try:

        # Пробуем превратить строку в JSON
        return json.loads(content)

    except Exception:

        # Если модель ответила не JSON,
        # возвращаем ошибку

        return {
            "status": "error",
            "message": content
        }