"""Маршруты HTML-страниц."""

from fastapi import APIRouter
from fastapi.responses import FileResponse


router = APIRouter()


@router.get("/")
def home():
    """Отдает главную страницу приложения."""

    return FileResponse("static/index.html")


@router.get("/teacher")
def teacher():
    """Return the teacher overview page."""

    return FileResponse("static/teacher.html")
