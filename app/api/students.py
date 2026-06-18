"""API routes for students and their task progress."""

from fastapi import APIRouter
from fastapi import HTTPException

from app.schemas import StudentCreateRequest
from app.services.progress import get_class_progress_map
from app.services.progress import get_progress_map
from app.services.progress import list_student_progress
from app.services.students import create_student
from app.services.students import find_or_create_student
from app.services.students import get_student
from app.services.students import list_students
from app.services.task_store import TASKS


router = APIRouter()


@router.post("/students")
def add_student(data: StudentCreateRequest):
    """Create a student record in the local SQLite database."""

    school = data.school.strip()
    class_name = data.class_name.strip()
    full_name = data.full_name.strip()

    if not school or not class_name or not full_name:
        raise HTTPException(
            status_code=400,
            detail="school, class_name and full_name are required"
        )

    return create_student(
        school,
        class_name,
        full_name
    )


@router.post("/students/login")
def login_student(data: StudentCreateRequest):
    """Find an existing student or create one for a first login."""

    school = data.school.strip()
    class_name = data.class_name.strip()
    full_name = data.full_name.strip()

    if not school or not class_name or not full_name:
        raise HTTPException(
            status_code=400,
            detail="school, class_name and full_name are required"
        )

    return find_or_create_student(
        school,
        class_name,
        full_name
    )


@router.get("/students")
def get_students():
    """Return all students."""

    return list_students()


@router.get("/students/{student_id}")
def get_student_by_id(student_id: int):
    """Return one student by id."""

    student = get_student(student_id)

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    return student


@router.get("/students/{student_id}/progress")
def get_progress_by_student(student_id: int):
    """Return current task progress for one student."""

    student = get_student(student_id)

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    return list_student_progress(student_id)


@router.get("/students/{student_id}/task-map")
def get_student_task_map(
    student_id: int,
    class_id: str,
    chapter: str,
    topic: str
):
    """Return all tasks in a section with this student's progress."""

    student = get_student(student_id)

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    tasks = [
        task
        for task in TASKS
        if task["class_id"] == class_id
        and task["chapter"] == chapter
        and task["topic"] == topic
    ]

    if not tasks:
        raise HTTPException(
            status_code=404,
            detail="Task section not found"
        )

    progress_by_number = get_progress_map(
        student_id,
        class_id,
        chapter,
        topic
    )

    def sort_key(task):
        try:
            return int(task["number"])
        except ValueError:
            return task["number"]

    result = []

    for task in sorted(tasks, key=sort_key):
        progress = progress_by_number.get(task["number"])

        result.append({
            "class_id": task["class_id"],
            "chapter": task["chapter"],
            "topic": task["topic"],
            "number": task["number"],
            "attempts_count": (
                progress["attempts_count"]
                if progress
                else 0
            ),
            "is_passed": (
                progress["is_passed"]
                if progress
                else 0
            ),
            "updated_at": (
                progress["updated_at"]
                if progress
                else None
            )
        })

    return result


@router.get("/students/{student_id}/class-task-map")
def get_student_class_task_map(
    student_id: int,
    class_id: str
):
    """Return all class tasks with this student's progress."""

    student = get_student(student_id)

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    tasks = [
        task
        for task in TASKS
        if task["class_id"] == class_id
    ]

    if not tasks:
        raise HTTPException(
            status_code=404,
            detail="Class not found"
        )

    progress_by_key = get_class_progress_map(
        student_id,
        class_id
    )

    def sort_key(task):
        return (
            int(task["chapter"]),
            int(task["topic"]),
            int(task["number"])
        )

    result = []

    for task in sorted(tasks, key=sort_key):
        key = (
            task["chapter"],
            task["topic"],
            task["number"]
        )
        progress = progress_by_key.get(key)

        result.append({
            "class_id": task["class_id"],
            "chapter": task["chapter"],
            "topic": task["topic"],
            "number": task["number"],
            "attempts_count": (
                progress["attempts_count"]
                if progress
                else 0
            ),
            "is_passed": (
                progress["is_passed"]
                if progress
                else 0
            ),
            "updated_at": (
                progress["updated_at"]
                if progress
                else None
            )
        })

    return result
