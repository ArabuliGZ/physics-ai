"""Маршруты HTML-страниц."""

from fastapi import APIRouter
from fastapi import Response
from fastapi.responses import FileResponse


router = APIRouter()


@router.get("/")
def home():
    """Отдает главную страницу приложения."""

    return FileResponse("static/index.html")


@router.head("/")
def home_head():
    """Let hosting health probes check the root page with HEAD."""

    return Response(status_code=200)


@router.get("/healthz")
def healthz():
    """Simple health check for reverse proxies and uptime monitors."""

    return {"status": "ok"}


@router.head("/healthz")
def healthz_head():
    """Let hosting health probes check health with HEAD."""

    return Response(status_code=200)


@router.get("/teacher")
def teacher():
    """Return the teacher overview page."""

    return FileResponse("static/teacher.html")
