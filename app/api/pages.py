"""Маршруты HTML-страниц."""

from fastapi import APIRouter
from fastapi.responses import FileResponse


router = APIRouter()


@router.get("/")
def home():
    """Отдает главную страницу приложения."""

    return FileResponse("static/index.html")

