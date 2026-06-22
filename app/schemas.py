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

    email: str | None = None
    school: str
    class_name: str | None = None
    grade: int | None = None
    class_group: str | None = None
    task_class_id: str | None = None
    full_name: str


class StudentLoginRequest(BaseModel):
    """Request body for student email login."""

    email: str
    password: str


class UserLoginRequest(BaseModel):
    """Request body for role-based user login."""

    email: str
    password: str


class AdminTeacherRequest(BaseModel):
    """Request body for creating or updating a teacher."""

    email: str
    full_name: str
    teacher_id: int | None = None


class AdminSchoolRequest(BaseModel):
    """Request body for creating or renaming a school."""

    name: str
    school_id: int | None = None


class AdminClassTeacherRequest(BaseModel):
    """Request body for assigning a class to another teacher."""

    teacher_id: int


class ClassUpdateRequest(BaseModel):
    """Request body for editing a teacher class row."""

    school: str
    grade: int
    class_group: str
    task_class_id: str
    teacher_id: int | None = None


class TeacherProgressOverrideRequest(BaseModel):
    """Request body for manually changing task progress from teacher journal."""

    student_id: int
    teacher_class_id: int | None = None
    class_id: str
    chapter: str
    topic: str
    number: str
    is_passed: bool
