"""Маршрут проверки решения через LLM."""

from fastapi import APIRouter

from app.schemas import CheckRequest
from app.services.media import image_to_base64
from app.services.media import is_image_file
from app.services.media import resolve_task_media_url
from llm import ask_llm


router = APIRouter()


@router.post("/check")
async def check(data: CheckRequest):
    """Проверяет решение ученика.

    Поведение сохранено: текст задачи, ответ ученика, история и картинки
    передаются в ask_llm, а результат модели возвращается frontend.
    """

    task_image_base64 = None

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

    return ask_llm(
        data.problem,
        data.solution,
        data.history,
        data.hint_level,
        data.problem_image_base64,
        task_image_base64
    )

