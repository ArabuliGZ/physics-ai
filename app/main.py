"""Сборка FastAPI-приложения.

В этом файле остаются только настройки уровня приложения:
подключение CORS, статических файлов и API-роутеров.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.check import router as check_router
from app.api.pages import router as pages_router
from app.api.students import router as students_router
from app.api.tasks import router as tasks_router
from app.database import init_database
from app.demo_seed import seed_demo_data


def is_demo_seed_enabled():
    """Return whether startup should create public demo data."""

    return os.getenv("SEED_DEMO_DATA", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def create_app():
    """Создает и настраивает экземпляр FastAPI.

    Отдельная функция удобна для будущих тестов: приложение можно будет
    создавать без побочных действий в тестовом окружении.
    """

    app = FastAPI()

    @app.on_event("startup")
    def startup():
        """Prepare local SQLite tables before the first request."""

        init_database()

        if is_demo_seed_enabled():
            seed_demo_data()

    # Раздаем frontend-файлы: HTML, CSS, JS и favicon.
    app.mount(
        "/static",
        StaticFiles(directory="static"),
        name="static"
    )

    # Раздаем исходные файлы задач и изображения по старому публичному пути.
    # Этот путь уже использует frontend, поэтому оставляем его без изменений.
    app.mount(
        "/tasks",
        StaticFiles(directory="tasks"),
        name="tasks"
    )

    # CORS оставлен таким же широким, как был до рефактора.
    # Это сохраняет текущее поведение при запуске frontend/backend отдельно.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Подключаем группы маршрутов. Пути внутри роутеров совпадают со старыми.
    app.include_router(pages_router)
    app.include_router(tasks_router)
    app.include_router(students_router)
    app.include_router(check_router)

    return app


# Переменная app нужна для запуска командой uvicorn app.main:app.
app = create_app()
