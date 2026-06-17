"""Работа с файлами условий задач.

Здесь собрана вся логика поиска png/jpg/pdf и конвертации изображений
в base64 для отправки в LLM.
"""

import base64
import mimetypes
import os

from fastapi import HTTPException


# Поддерживаемые расширения файлов условий.
TASK_MEDIA_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".pdf",
)


def resolve_task_media(group, media_name):
    """Находит файл условия задачи на диске.

    media_name может быть как с расширением, так и без него. Поиск без
    учета регистра нужен для файлов вроде 6.4.1.JPG.
    """

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

    if name_ext.lower() in TASK_MEDIA_EXTENSIONS:

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


def resolve_task_media_url(url):
    """Преобразует публичный URL файла условия в локальный путь."""

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
    """Определяет MIME-тип файла по имени."""

    mime_type, _ = mimetypes.guess_type(path)

    return mime_type or "application/octet-stream"


def is_image_file(path):
    """Проверяет, можно ли отправлять файл в LLM как изображение."""

    return get_mime_type(path).startswith(
        "image/"
    )


def image_to_base64(path):
    """Кодирует изображение в data URL для multimodal-запроса."""

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
