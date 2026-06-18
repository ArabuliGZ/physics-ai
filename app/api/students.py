"""API routes for students and their task progress."""

import csv
from io import StringIO

from fastapi import APIRouter
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import UploadFile

from app.schemas import StudentCreateRequest
from app.schemas import StudentLoginRequest
from app.schemas import TeacherProgressOverrideRequest
from app.services.progress import get_class_progress_map
from app.services.progress import get_progress_map
from app.services.progress import list_teacher_journal_progress
from app.services.progress import list_student_progress
from app.services.progress import set_task_progress_passed
from app.services.students import allowed_task_class_id
from app.services.students import create_student
from app.services.students import deactivate_student
from app.services.students import find_student_by_email
from app.services.students import get_student
from app.services.students import list_students
from app.services.students import list_students_with_summary
from app.services.students import upsert_student_by_email
from app.services.task_store import TASKS


router = APIRouter()


@router.post("/students")
def add_student(data: StudentCreateRequest):
    """Create a student record in the local SQLite database."""

    school = data.school.strip()
    email = data.email.strip().lower() if data.email else None
    class_name = data.class_name.strip() if data.class_name else None
    class_group = data.class_group.strip() if data.class_group else None
    task_class_id = data.task_class_id.strip() if data.task_class_id else None
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
        task_class_id=task_class_id,
        email=email,
    )


@router.post("/students/login")
def login_student(data: StudentLoginRequest):
    """Find an existing student by email."""

    email = data.email.strip().lower()

    if not email:
        raise HTTPException(
            status_code=400,
            detail="email is required"
        )

    student = find_student_by_email(email)

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Student with this email was not found"
        )

    return student


@router.get("/students")
def get_students():
    """Return all students."""

    return list_students()


@router.get("/teacher/students")
def get_teacher_students():
    """Return students with progress totals for the teacher page."""

    return list_students_with_summary()


@router.post("/teacher/import-students")
async def import_teacher_students(
    school: str = Form(...),
    grade: int = Form(...),
    class_group: str = Form(...),
    task_class_id: str = Form(...),
    file: UploadFile = File(...),
):
    """Import students from a CSV file with full_name and email columns."""

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported"
        )

    content = await file.read()

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise HTTPException(
            status_code=400,
            detail="CSV must be encoded as UTF-8"
        ) from error

    reader = csv.DictReader(StringIO(text))

    if reader.fieldnames is None:
        raise HTTPException(
            status_code=400,
            detail="CSV header is required"
        )

    created = 0
    updated = 0
    errors = []

    for row_number, row in enumerate(reader, start=2):
        full_name = get_csv_value(row, "full_name", "фио", "ФИО")
        email = get_csv_value(row, "email", "почта", "Email")

        if not full_name or not email:
            errors.append({
                "row": row_number,
                "error": "full_name and email are required"
            })
            continue

        if "@" not in email:
            errors.append({
                "row": row_number,
                "error": "email is invalid"
            })
            continue

        student = upsert_student_by_email(
            email=email,
            full_name=full_name,
            school=school.strip(),
            grade=grade,
            class_group=class_group.strip(),
            task_class_id=task_class_id.strip(),
        )

        if student["action"] == "created":
            created += 1
        else:
            updated += 1

    return {
        "created": created,
        "updated": updated,
        "errors": errors,
    }


@router.post("/teacher/students")
def upsert_teacher_student(data: StudentCreateRequest):
    """Create or update one student by email from the teacher page."""

    if not data.email:
        raise HTTPException(
            status_code=400,
            detail="email is required"
        )

    if not data.school or data.grade is None or not data.class_group or not data.full_name:
        raise HTTPException(
            status_code=400,
            detail="school, grade, class_group and full_name are required"
        )

    student = upsert_student_by_email(
        email=data.email,
        full_name=data.full_name.strip(),
        school=data.school.strip(),
        grade=data.grade,
        class_group=data.class_group.strip(),
        task_class_id=(
            data.task_class_id.strip()
            if data.task_class_id
            else f"{data.grade}class"
        ),
    )

    return student


@router.post("/teacher/students/{student_id}/deactivate")
def deactivate_teacher_student(student_id: int):
    """Hide one student from teacher journals without deleting history."""

    result = deactivate_student(student_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Active student not found"
        )

    return result


@router.post("/teacher/progress")
def override_teacher_progress(data: TeacherProgressOverrideRequest):
    """Manually set whether a student's task is passed from the teacher journal."""

    student = get_student(data.student_id)

    if student is None or student["is_active"] != 1:
        raise HTTPException(
            status_code=404,
            detail="Active student not found"
        )

    if data.class_id != allowed_task_class_id(student):
        raise HTTPException(
            status_code=403,
            detail="This task base is not available for the selected student"
        )

    task_exists = any(
        task["class_id"] == data.class_id
        and task["chapter"] == data.chapter
        and task["topic"] == data.topic
        and task["number"] == data.number
        for task in TASKS
    )

    if not task_exists:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    return set_task_progress_passed(
        data.student_id,
        data.class_id,
        data.chapter,
        data.topic,
        data.number,
        data.is_passed,
    )


def get_csv_value(row, *names):
    """Read a CSV value by any supported column name."""

    normalized = {
        key.strip().lower(): value
        for key, value in row.items()
        if key is not None
    }

    for name in names:
        value = normalized.get(name.strip().lower())

        if value:
            return value.strip()

    return ""


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
        and student["task_class_id"] == class_id
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

    if class_id != allowed_task_class_id(student):
        raise HTTPException(
            status_code=403,
            detail="This task base is not available for the selected student"
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

    if class_id != allowed_task_class_id(student):
        raise HTTPException(
            status_code=403,
            detail="This task base is not available for the selected student"
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
