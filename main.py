# ===== ИМПОРТ БИБЛИОТЕК =====

# Основной класс FastAPI для создания сервера
from fastapi import FastAPI
from fastapi import HTTPException

# BaseModel нужен для описания структуры данных,
# которые приходят от frontend
from pydantic import BaseModel

# Middleware для разрешения запросов с frontend
from fastapi.middleware.cors import CORSMiddleware

# Позволяет раздавать статические файлы:
# HTML, CSS, JS, картинки
from fastapi.staticfiles import StaticFiles

# Позволяет отправлять файл пользователю
from fastapi.responses import FileResponse

# Импорт функции для обращения к LLM
from llm import ask_llm

# Библиотека для работы с JSON
import json

# Библиотека для работы с файлами и папками
import os

import base64
import mimetypes

# ===== СОЗДАНИЕ FASTAPI ПРИЛОЖЕНИЯ =====

app = FastAPI()


# =========================================================
# ===== ЗАГРУЗКА ВСЕХ ЗАДАЧ ИЗ JSON ФАЙЛОВ В ПАМЯТЬ =====
# =========================================================

# Здесь будут храниться все задачи
TASKS = []
GROUPS = []

TASK_MEDIA_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".pdf",
)

# Папка с задачами
tasks_folder = "tasks"

# Перебираем все файлы в папке tasks
for filename in os.listdir(tasks_folder):

    # Берем только JSON файлы
    if filename.endswith(".json"):

        # Создаем полный путь к файлу
        path = os.path.join(
            tasks_folder,
            filename
        )

        # Открываем JSON файл
        with open(path, "r", encoding="utf-8") as f:

            # Загружаем данные из JSON
            data = json.load(f)

            # Добавляем задачи в общий список TASKS
            TASKS.extend(data)

with open(
    "tasks/groups.json",
    "r",
    encoding="utf-8"
) as f:

    GROUPS = json.load(f)


# ==========================================
# ===== ПОДКЛЮЧЕНИЕ СТАТИЧЕСКИХ ФАЙЛОВ =====
# ==========================================

# Подключаем папку static
# По адресу /static будут доступны:
# CSS, JS, картинки и т.д.
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

# Подключаем папку tasks
# Это нужно, например, чтобы открывать картинки задач
app.mount(
    "/tasks",
    StaticFiles(directory="tasks"),
    name="tasks"
)


# =========================
# ===== НАСТРОЙКА CORS =====
# =========================

# CORS нужен, чтобы frontend мог обращаться к backend
# Особенно важно, если frontend и backend работают
# на разных портах

app.add_middleware(
    CORSMiddleware,

    # Разрешаем запросы от любых сайтов
    allow_origins=["*"],

    # Разрешаем отправку cookies и авторизации
    allow_credentials=True,

    # Разрешаем любые HTTP методы:
    # GET, POST, PUT, DELETE и т.д.
    allow_methods=["*"],

    # Разрешаем любые заголовки
    allow_headers=["*"],
)


# ======================
# ===== МОДЕЛИ API =====
# ======================

# Описание структуры данных,
# которые приходят на endpoint /check

class CheckRequest(BaseModel):

    # Условие задачи
    problem: str

    # Решение ученика
    solution: str

    # История общения
    history: list = []

    # Уровень подсказки
    hint_level: int

    # Картинка
    problem_image_base64: str | None = None

    task_image_url: str | None = None


# ======================
# ===== API ROUTES =====
# ======================

# Главная страница сайта
@app.get("/")
def home():

    # Отправляем файл index.html
    return FileResponse("static/index.html")


# Endpoint для проверки решения
@app.post("/check")
async def check(data: CheckRequest):

    # Отправляем задачу и решение в LLM
    task_image_base64 = None
    
    if data.task_image_url:

        local_path = resolve_task_media_url(
            data.task_image_url
        )

        if is_image_file(local_path):

            task_image_base64 = image_to_base64(
                local_path
            )

    result = ask_llm(
        data.problem,
        data.solution,
        data.history,
        data.hint_level,
        data.problem_image_base64,
        task_image_base64
    )

    # Возвращаем ответ модели
    return result


# Endpoint для получения всех задач
@app.get("/tasks")
def get_tasks():

    # Возвращаем список задач
    return [
        build_task_response(task)
        for task in TASKS
    ]

@app.get("/groups")
def get_groups():

    return GROUPS

@app.get("/task-media/{group}/{media_name}")
def get_task_media(group: str, media_name: str):

    path = resolve_task_media(
        group,
        media_name
    )

    return FileResponse(path)


@app.get("/task-media-info/{group}/{media_name}")
def get_task_media_info(group: str, media_name: str):

    path = resolve_task_media(
        group,
        media_name
    )

    mime_type = get_mime_type(path)

    return {
        "url": f"/task-media/{group}/{media_name}",
        "mime_type": mime_type,
        "is_pdf": mime_type == "application/pdf",
        "is_image": mime_type.startswith("image/")
    }


def resolve_task_media(group, media_name):

    safe_group = os.path.basename(group)
    safe_name = os.path.basename(media_name)

    base_path = os.path.join(
        "tasks",
        "images",
        safe_group
    )

    _, name_ext = os.path.splitext(
        safe_name
    )

    if name_ext:

        candidates = [safe_name]

    else:

        candidates = [
            safe_name + extension
            for extension in TASK_MEDIA_EXTENSIONS
        ]

    for candidate in candidates:

        path = os.path.join(
            base_path,
            candidate
        )

        if os.path.isfile(path):

            return path

    if os.path.isdir(base_path):

        lower_candidates = {
            candidate.lower()
            for candidate in candidates
        }

        for filename in os.listdir(base_path):

            if filename.lower() in lower_candidates:

                return os.path.join(
                    base_path,
                    filename
                )

    raise HTTPException(
        status_code=404,
        detail="Task media not found"
    )


def build_task_response(task):

    response = dict(task)

    if not task.get("image"):

        response["image_url"] = None
        response["image_mime_type"] = None
        response["image_is_pdf"] = False
        response["image_is_image"] = False

        return response

    try:

        path = resolve_task_media(
            task.get("group", ""),
            task["image"]
        )

    except HTTPException:

        response["image_url"] = None
        response["image_mime_type"] = None
        response["image_is_pdf"] = False
        response["image_is_image"] = False

        return response

    filename = os.path.basename(path)
    mime_type = get_mime_type(path)

    response["image_url"] = (
        "/tasks/images/"
        + task["group"]
        + "/"
        + filename
    )
    response["image_mime_type"] = mime_type
    response["image_is_pdf"] = mime_type == "application/pdf"
    response["image_is_image"] = mime_type.startswith("image/")

    return response


def resolve_task_media_url(url):

    parts = url.strip("/").split("/")

    if len(parts) >= 3 and parts[0] == "task-media":

        return resolve_task_media(
            parts[1],
            parts[2]
        )

    if len(parts) >= 4 and parts[0] == "tasks" and parts[1] == "images":

        return resolve_task_media(
            parts[2],
            parts[3]
        )

    raise HTTPException(
        status_code=400,
        detail="Unsupported task media url"
    )


def get_mime_type(path):

    mime_type, _ = mimetypes.guess_type(path)

    return mime_type or "application/octet-stream"


def is_image_file(path):

    return get_mime_type(path).startswith(
        "image/"
    )


# Вспомогательная функция, импортирующая в base64
def image_to_base64(path):

    with open(path, "rb") as f:

        encoded = base64.b64encode(
            f.read()
        ).decode("utf-8")

    return (
        "data:"
        + get_mime_type(path)
        + ";base64,"
        + encoded
    )
