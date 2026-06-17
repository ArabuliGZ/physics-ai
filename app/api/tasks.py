"""Маршруты для задач, групп и файлов условий."""

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.services.media import get_mime_type
from app.services.media import resolve_task_media
from app.services.task_store import GROUPS
from app.services.task_store import TASKS
from app.services.task_store import build_task_response


router = APIRouter()


@router.get("/tasks")
def get_tasks():
    """Возвращает список задач в том же формате, что и раньше.

    Дополнительно к старым полям добавляются image_url/image_mime_type,
    чтобы frontend мог открыть png, jpg и pdf без угадывания расширения.
    """

    return [
        build_task_response(task)
        for task in TASKS
    ]


@router.get("/groups")
def get_groups():
    """Возвращает список учебных групп/классов."""

    return GROUPS


@router.get("/task-media/{group}/{media_name}")
def get_task_media(group: str, media_name: str):
    """Отдает файл условия по имени без жесткой привязки к .png."""

    path = resolve_task_media(
        group,
        media_name
    )

    return FileResponse(path)


@router.get("/task-media-info/{group}/{media_name}")
def get_task_media_info(group: str, media_name: str):
    """Возвращает информацию о файле условия.

    Маршрут оставлен для совместимости: даже если frontend сейчас берет
    image_url из /tasks, старый запасной механизм продолжит работать.
    """

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

