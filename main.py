# ===== ИМПОРТ БИБЛИОТЕК =====

# Основной класс FastAPI для создания сервера
from fastapi import FastAPI

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


# ===== СОЗДАНИЕ FASTAPI ПРИЛОЖЕНИЯ =====

app = FastAPI()


# =========================================================
# ===== ЗАГРУЗКА ВСЕХ ЗАДАЧ ИЗ JSON ФАЙЛОВ В ПАМЯТЬ =====
# =========================================================

# Здесь будут храниться все задачи
TASKS = []

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
    
    #История общения
    history: list = []

    #Уровень подсказки
    hint_level: int


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
    result = ask_llm(
        data.problem,
        data.solution,
        data.history,
        data.hint_level
    )

    # Возвращаем ответ модели
    return result


# Endpoint для получения всех задач
@app.get("/tasks")
def get_tasks():

    # Возвращаем список задач
    return TASKS