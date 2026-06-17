"""Сборка FastAPI-приложения.

В этом файле остаются только настройки уровня приложения:
подключение CORS, статических файлов и API-роутеров.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.check import router as check_router
from app.api.pages import router as pages_router
from app.api.tasks import router as tasks_router


def create_app():
    """Создает и настраивает экземпляр FastAPI.

    Отдельная функция удобна для будущих тестов: приложение можно будет
    создавать без побочных действий в тестовом окружении.
    """

    app = FastAPI()

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
    app.include_router(check_router)

    return app


# Переменная app нужна для запуска командой uvicorn app.main:app.
app = create_app()

