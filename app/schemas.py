"""Pydantic-схемы входящих API-запросов."""

from pydantic import BaseModel


class CheckRequest(BaseModel):
    """Тело запроса /check от frontend."""

    # Условие выбранной задачи.
    problem: str

    # Решение или вопрос ученика.
    solution: str

    # История диалога с AI по текущей задаче.
    history: list = []

    # Уровень подсказки: 0-3.
    hint_level: int

    # Картинка, которую приложил ученик к своему решению.
    problem_image_base64: str | None = None

    # URL картинки/файла условия выбранной задачи.
    task_image_url: str | None = None

    # Student and task identifiers are optional for backward compatibility.
    student_id: int | None = None
    class_id: str | None = None
    chapter: str | None = None
    topic: str | None = None
    number: str | None = None


class StudentCreateRequest(BaseModel):
    """Request body for creating a student profile."""

    school: str
    class_name: str
    full_name: str
