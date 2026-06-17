"""Загрузка задач и подготовка данных для frontend."""

import json
import os

from fastapi import HTTPException

from app.services.media import get_mime_type
from app.services.media import resolve_task_media


# Глобальные списки повторяют старое поведение main.py:
# данные загружаются один раз при старте приложения и дальше читаются из памяти.
TASKS = []
GROUPS = []


def load_tasks(tasks_folder="tasks"):
    """Загружает все JSON-файлы с задачами из папки tasks.

    После перехода на явный контракт задач groups.json больше не считается
    файлом с задачами. Поэтому берем только файлы вида 7class.json.
    """

    tasks = []

    for filename in os.listdir(tasks_folder):

        if not filename.endswith("class.json"):

            continue

        path = os.path.join(
            tasks_folder,
            filename
        )

        with open(path, "r", encoding="utf-8") as f:

            data = json.load(f)

        tasks.extend(data)

    return tasks


def load_groups(path="tasks/groups.json"):
    """Загружает список классов/групп."""

    with open(path, "r", encoding="utf-8") as f:

        return json.load(f)


def build_task_response(task):
    """Добавляет к задаче сведения о файле условия.

    Поля class_id/chapter/topic/number остаются как есть. Дополнительные
    поля image_* помогают frontend понять, какой файл открыть: png, jpg
    или pdf.
    """

    response = dict(task)

    if not task.get("image"):

        response["image_url"] = None
        response["image_mime_type"] = None
        response["image_is_pdf"] = False
        response["image_is_image"] = False

        return response

    try:

        path = resolve_task_media(
            task.get("class_id", ""),
            task["image"]
        )

    except HTTPException:

        response["image_url"] = None
        response["image_mime_type"] = None
        response["image_is_pdf"] = False
        response["image_is_image"] = False

        return response

    filename = os.path.basename(path)
    mime_type = get_mime_type(path)

    response["image_url"] = (
        "/tasks/images/"
        + task["class_id"]
        + "/"
        + filename
    )
    response["image_mime_type"] = mime_type
    response["image_is_pdf"] = mime_type == "application/pdf"
    response["image_is_image"] = mime_type.startswith("image/")

    return response


TASKS = load_tasks()
GROUPS = load_groups()
