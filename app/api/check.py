"""Маршрут проверки решения через LLM."""

from fastapi import APIRouter
from fastapi import Header
from fastapi import HTTPException

from app.schemas import CheckRequest
from app.services.media import image_to_base64
from app.services.media import is_image_file
from app.services.media import resolve_task_media_url
from app.services.progress import get_task_progress
from app.services.progress import record_task_attempt
from app.services.sessions import find_student_by_session_token
from app.services.students import allowed_task_class_id
from app.services.students import get_student
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


@router.post("/check")
async def check(
    data: CheckRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    """Проверяет решение ученика.

    Поведение сохранено: текст задачи, ответ ученика, история и картинки
    передаются в ask_llm, а результат модели возвращается frontend.
    """

    task_image_base64 = None
    has_tracking_data = (
        data.student_id is not None
        and data.class_id is not None
        and data.chapter is not None
        and data.topic is not None
        and data.number is not None
    )
    token = bearer_token(authorization)
    session_student = find_student_by_session_token(token) if token else None

    if (
        has_tracking_data
        and session_student is not None
        and int(session_student["id"]) != int(data.student_id)
    ):
        raise HTTPException(
            status_code=403,
            detail="Student session does not match submitted student"
        )

    student = (
        session_student
        if session_student is not None
        else get_student(data.student_id) if has_tracking_data else None
    )

    if (
        has_tracking_data
        and student is not None
        and data.class_id != allowed_task_class_id(student)
    ):
        raise HTTPException(
            status_code=403,
            detail="This task base is not available for the selected student"
        )

    # Если у задачи есть файл условия, прикладываем его к LLM только
    # когда это изображение. PDF показывается ученику, но не отправляется
    # в текущий image_url-формат запроса к модели.
    if data.task_image_url:

        local_path = resolve_task_media_url(
            data.task_image_url
        )

        if is_image_file(local_path):

            task_image_base64 = image_to_base64(
                local_path
            )

    result = ask_llm(
        data.problem,
        data.solution,
        data.history,
        data.hint_level,
        data.problem_image_base64,
        task_image_base64
    )

    result["attempt_saved"] = False
    result["attempt_id"] = None
    result["progress"] = None

    if has_tracking_data and student is not None:
        attempt = record_task_attempt(
            student_id=data.student_id,
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
            data.student_id,
            data.class_id,
            data.chapter,
            data.topic,
            data.number
        )

    return result
