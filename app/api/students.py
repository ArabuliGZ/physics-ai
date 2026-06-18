"""API routes for students and their task progress."""

from fastapi import APIRouter
from fastapi import HTTPException

from app.schemas import StudentCreateRequest
from app.services.progress import get_class_progress_map
from app.services.progress import get_progress_map
from app.services.progress import list_teacher_journal_progress
from app.services.progress import list_student_progress
from app.services.students import create_student
from app.services.students import find_or_create_student
from app.services.students import get_student
from app.services.students import list_students
from app.services.students import list_students_with_summary
from app.services.task_store import TASKS


router = APIRouter()


@router.post("/students")
def add_student(data: StudentCreateRequest):
    """Create a student record in the local SQLite database."""

    school = data.school.strip()
    class_name = data.class_name.strip() if data.class_name else None
    class_group = data.class_group.strip() if data.class_group else None
    full_name = data.full_name.strip()

    if not school or (data.grade is None and not class_name) or not full_name:
        raise HTTPException(
            status_code=400,
            detail="school, grade or class_name, and full_name are required"
        )

    return create_student(
        school,
        class_name,
        full_name,
        grade=data.grade,
        class_group=class_group,
    )


@router.post("/students/login")
def login_student(data: StudentCreateRequest):
    """Find an existing student or create one for a first login."""

    school = data.school.strip()
    class_name = data.class_name.strip() if data.class_name else None
    class_group = data.class_group.strip() if data.class_group else None
    full_name = data.full_name.strip()

    if not school or (data.grade is None and not class_name) or not full_name:
        raise HTTPException(
            status_code=400,
            detail="school, grade or class_name, and full_name are required"
        )

    return find_or_create_student(
        school,
        class_name,
        full_name,
        grade=data.grade,
        class_group=class_group,
    )


@router.get("/students")
def get_students():
    """Return all students."""

    return list_students()


@router.get("/teacher/students")
def get_teacher_students():
    """Return students with progress totals for the teacher page."""

    return list_students_with_summary()


@router.get("/teacher/journal")
def get_teacher_journal(
    school: str,
    grade: int,
    class_group: str,
    class_id: str
):
    """Return a teacher journal: one row per student and one column per task."""

    normalized_group = class_group.strip()

    students = [
        student
        for student in list_students_with_summary()
        if student["school"] == school
        and student["grade"] == grade
        and (student["class_group"] or "") == normalized_group
    ]

    tasks = [
        task
        for task in TASKS
        if task["class_id"] == class_id
    ]

    if not tasks:
        raise HTTPException(
            status_code=404,
            detail="Task base not found"
        )

    def task_sort_key(task):
        return (
            int(task["chapter"]),
            int(task["topic"]),
            int(task["number"])
        )

    task_refs = [
        {
            "class_id": task["class_id"],
            "chapter": task["chapter"],
            "topic": task["topic"],
            "number": task["number"],
        }
        for task in sorted(tasks, key=task_sort_key)
    ]

    progress = list_teacher_journal_progress(
        [student["id"] for student in students],
        class_id
    )

    return {
        "students": students,
        "tasks": task_refs,
        "progress": progress,
    }


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
