"""Маршруты HTML-страниц."""

from fastapi import APIRouter
from fastapi.responses import FileResponse


router = APIRouter()


@router.get("/")
def home():
    """Отдает главную страницу приложения."""

    return FileResponse("static/index.html")


@router.get("/healthz")
def healthz():
    """Simple health check for reverse proxies and uptime monitors."""

    return {"status": "ok"}


@router.get("/teacher")
def teacher():
    """Return the teacher overview page."""

    return FileResponse("static/teacher.html")
