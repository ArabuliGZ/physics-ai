"""Маршруты HTML-страниц."""

from fastapi import APIRouter
from fastapi import Request
from fastapi import Response
from fastapi.responses import FileResponse
from fastapi.responses import RedirectResponse


router = APIRouter()


HTML_NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}

TEACHER_PAGE_VERSION = "admin-llm-settings-20260730"


@router.get("/")
def home():
    """Отдает главную страницу приложения."""

    return FileResponse("static/index.html", headers=HTML_NO_CACHE_HEADERS)


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
def teacher(request: Request):
    """Return the teacher overview page."""

    if request.query_params.get("ui") != TEACHER_PAGE_VERSION:
        params = dict(request.query_params)
        params["ui"] = TEACHER_PAGE_VERSION
        redirect_url = str(request.url.include_query_params(**params))
        return RedirectResponse(
            redirect_url,
            status_code=307,
            headers=HTML_NO_CACHE_HEADERS,
        )

    return FileResponse("static/teacher.html", headers=HTML_NO_CACHE_HEADERS)
