"""Маршрут проверки решения через LLM."""

from fastapi import APIRouter
from fastapi import Header
from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool

from app.schemas import CheckRequest
from app.services.media import image_to_base64
from app.services.media import is_image_file
from app.services.media import resolve_task_media
from app.services.progress import get_task_progress
from app.services.progress import record_task_attempt
from app.services.sessions import find_student_by_session_token
from app.services.solution_attachments import convert_heic_data_url_to_jpeg
from app.services.students import allowed_task_class_id
from app.services.task_store import find_task
from config import ALLOWED_SOLUTION_ATTACHMENT_MIME_TYPES
from config import HEIC_SOLUTION_ATTACHMENT_MIME_TYPES
from config import MAX_SOLUTION_IMAGE_BYTES
from llm import ask_llm


router = APIRouter()


def bearer_token(authorization):
    """Extract a bearer token from the Authorization header."""

    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token:
        return None

    return token.strip()


def base64_payload_size(data_url):
    """Return decoded byte size for a base64 data URL without decoding it."""

    if not data_url:
        return 0

    _, separator, payload = data_url.partition(",")
    encoded = payload if separator else data_url
    encoded = "".join(encoded.split())
    padding = len(encoded) - len(encoded.rstrip("="))

    return (len(encoded) * 3) // 4 - padding


def data_url_mime_type(data_url):
    """Return MIME type from a data URL, or None when there is no header."""

    if not data_url or not data_url.startswith("data:"):
        return None

    header, _, _ = data_url.partition(",")
    mime_type = header[5:].split(";", 1)[0].lower()

    return mime_type or None


@router.post("/check")
async def check(
    data: CheckRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    """Проверяет решение ученика.

    Условие, ответ и файл задачи всегда берутся из серверной базы. Клиент
    передает только идентификаторы задачи и решение ученика.
    """

    task_image_base64 = None
    solution_image_base64 = data.problem_image_base64
    token = bearer_token(authorization)
    session_student = find_student_by_session_token(token) if token else None

    if session_student is None:
        raise HTTPException(
            status_code=401,
            detail="Student login is required"
        )

    if (
        data.student_id is not None
        and int(session_student["id"]) != int(data.student_id)
    ):
        raise HTTPException(
            status_code=403,
            detail="Student session does not match submitted student"
        )

    task_identifiers = (
        data.class_id,
        data.chapter,
        data.topic,
        data.number,
    )

    if any(value is None or not str(value).strip() for value in task_identifiers):
        raise HTTPException(
            status_code=400,
            detail="Task identifiers are required"
        )

    if data.class_id != allowed_task_class_id(session_student):
        raise HTTPException(
            status_code=403,
            detail="This task base is not available for the selected student"
        )

    task = find_task(
        data.class_id,
        data.chapter,
        data.topic,
        data.number,
    )

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    # Если у задачи есть файл условия, прикладываем его к LLM только
    # когда это изображение. PDF показывается ученику, но не отправляется
    # в текущий image_url-формат запроса к модели.
    if solution_image_base64:
        mime_type = data_url_mime_type(solution_image_base64)

        if mime_type not in ALLOWED_SOLUTION_ATTACHMENT_MIME_TYPES:
            raise HTTPException(
                status_code=415,
                detail=(
                    "В запрос можно отправить только изображение "
                    "JPG, PNG, WEBP, HEIC или HEIF."
                )
            )

        if base64_payload_size(solution_image_base64) > MAX_SOLUTION_IMAGE_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Файл слишком большой. Максимальный размер — 10 МБ."
            )

        if mime_type in HEIC_SOLUTION_ATTACHMENT_MIME_TYPES:
            try:
                solution_image_base64 = convert_heic_data_url_to_jpeg(
                    solution_image_base64
                )
            except ValueError as error:
                raise HTTPException(
                    status_code=415,
                    detail="Не получилось прочитать файл HEIC или HEIF."
                ) from error

    if task.get("image"):
        try:
            local_path = resolve_task_media(
                task["class_id"],
                task["image"],
            )
        except HTTPException as error:
            if error.status_code != 404:
                raise
        else:
            if is_image_file(local_path):
                task_image_base64 = image_to_base64(local_path)

    reference_answer = task.get("answer")

    result = await run_in_threadpool(
        ask_llm,
        task["problem"],
        data.solution,
        data.history,
        data.hint_level,
        solution_image_base64,
        task_image_base64,
        reference_answer,
    )

    result["attempt_saved"] = False
    result["attempt_id"] = None
    result["progress"] = None

    student_id = int(session_student["id"])
    attempt = record_task_attempt(
        student_id=student_id,
        class_id=data.class_id,
        chapter=data.chapter,
        topic=data.topic,
        number=data.number,
        solution_text=data.solution,
        ai_response=result.get("message"),
        is_passed=bool(result.get("is_passed"))
    )

    result["attempt_saved"] = True
    result["attempt_id"] = attempt["id"]
    result["progress"] = get_task_progress(
        student_id,
        data.class_id,
        data.chapter,
        data.topic,
        data.number
    )

    return result
