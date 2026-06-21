"""API routes for students and their task progress."""

import csv
from io import StringIO
from urllib.parse import quote

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import Header
from fastapi import HTTPException
from fastapi import Response
from fastapi import UploadFile

from app.schemas import StudentCreateRequest
from app.schemas import StudentLoginRequest
from app.schemas import AdminClassTeacherRequest
from app.schemas import AdminSchoolRequest
from app.schemas import AdminTeacherRequest
from app.schemas import TeacherProgressOverrideRequest
from app.schemas import UserLoginRequest
from app.services.classes import deactivate_teacher_class
from app.services.classes import ensure_teacher_class
from app.services.classes import get_teacher_class
from app.services.classes import list_admin_classes
from app.services.classes import list_teacher_classes
from app.services.classes import restore_teacher_class
from app.services.classes import update_class_teacher
from app.services.progress import get_class_progress_map
from app.services.progress import get_progress_map
from app.services.progress import list_teacher_journal_progress
from app.services.progress import list_student_progress
from app.services.progress import set_task_progress_passed
from app.services.schools import active_school_exists
from app.services.schools import deactivate_school
from app.services.schools import list_admin_schools
from app.services.schools import list_active_schools
from app.services.schools import restore_school
from app.services.schools import upsert_school
from app.services.students import allowed_task_class_id
from app.services.students import create_student
from app.services.students import deactivate_student
from app.services.students import find_student_by_email
from app.services.students import get_student
from app.services.students import list_students
from app.services.students import list_students_with_summary
from app.services.students import upsert_student_by_email
from app.services.task_store import TASKS
from app.services.users import deactivate_teacher
from app.services.users import find_user_by_email
from app.services.users import get_active_teacher
from app.services.users import list_admin_teachers
from app.services.users import restore_teacher
from app.services.users import upsert_teacher


router = APIRouter()


def require_teacher_user(x_user_email: str | None = Header(default=None, alias="X-User-Email")):
    """Return the current teacher/admin user from a temporary email header."""

    if not x_user_email:
        raise HTTPException(
            status_code=401,
            detail="Teacher login is required"
        )

    user = find_user_by_email(x_user_email)

    if user is None or user["role"] not in ("teacher", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Teacher access is required"
        )

    return user


def teacher_scope_id(user):
    """Return teacher id for filtering, or None when admin can see all."""

    if user["role"] == "admin":
        return None

    return user["id"]


def require_admin_user(current_user=Depends(require_teacher_user)):
    """Return the current user only when they are an administrator."""

    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access is required"
        )

    return current_user


@router.post("/auth/login")
def login_user(data: UserLoginRequest):
    """Login a role-based user by email."""

    email = data.email.strip().lower()

    if not email:
        raise HTTPException(
            status_code=400,
            detail="email is required"
        )

    user = find_user_by_email(email)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User with this email was not found"
        )

    return user


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
def get_teacher_students(current_user=Depends(require_teacher_user)):
    """Return students with progress totals for the teacher page."""

    return list_students_with_summary(teacher_scope_id(current_user))


@router.get("/teacher/classes")
def get_teacher_classes(current_user=Depends(require_teacher_user)):
    """Return active class records for the teacher page."""

    return list_teacher_classes(teacher_scope_id(current_user))


@router.get("/teacher/schools")
def get_teacher_schools(current_user=Depends(require_teacher_user)):
    """Return schools available for creating teacher classes."""

    return list_active_schools()


@router.post("/teacher/classes/{class_id}/deactivate")
def deactivate_class(class_id: int, current_user=Depends(require_teacher_user)):
    """Archive a class and hide its students from active teacher views."""

    result = deactivate_teacher_class(class_id, teacher_scope_id(current_user))

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Active class not found"
        )

    return result


@router.get("/admin/schools")
def get_admin_schools(current_user=Depends(require_admin_user)):
    """Return all schools for the admin panel."""

    return list_admin_schools()


@router.post("/admin/schools")
def upsert_admin_school(
    data: AdminSchoolRequest,
    current_user=Depends(require_admin_user),
):
    """Create a school or rename an existing school."""

    name = data.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="name is required"
        )

    result = upsert_school(name, data.school_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="School not found"
        )

    if result.get("blocked"):
        raise HTTPException(
            status_code=409,
            detail="School already exists"
        )

    return result


@router.post("/admin/schools/{school_id}/deactivate")
def deactivate_admin_school(school_id: int, current_user=Depends(require_admin_user)):
    """Archive a school when no active classes depend on it."""

    result = deactivate_school(school_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Active school not found"
        )

    if result.get("blocked"):
        raise HTTPException(
            status_code=409,
            detail="School has active classes"
        )

    return result


@router.post("/admin/schools/{school_id}/restore")
def restore_admin_school(school_id: int, current_user=Depends(require_admin_user)):
    """Restore an archived school."""

    result = restore_school(school_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Archived school not found"
        )

    return result


@router.get("/admin/classes")
def get_admin_classes(current_user=Depends(require_admin_user)):
    """Return active and archived classes for the admin panel."""

    return list_admin_classes()


@router.post("/admin/classes/{class_id}/teacher")
def update_admin_class_teacher(
    class_id: int,
    data: AdminClassTeacherRequest,
    current_user=Depends(require_admin_user),
):
    """Assign a class to another active teacher."""

    result = update_class_teacher(class_id, data.teacher_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Class not found"
        )

    if result.get("blocked"):
        raise HTTPException(
            status_code=404,
            detail="Active teacher not found"
        )

    return result


@router.post("/admin/classes/{class_id}/restore")
def restore_admin_class(class_id: int, current_user=Depends(require_admin_user)):
    """Restore an archived class."""

    result = restore_teacher_class(class_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Archived class not found"
        )

    return result


@router.get("/admin/teachers")
def get_admin_teachers(current_user=Depends(require_admin_user)):
    """Return teachers for the admin panel."""

    return list_admin_teachers()


@router.post("/admin/teachers")
def upsert_admin_teacher(
    data: AdminTeacherRequest,
    current_user=Depends(require_admin_user),
):
    """Create or update a teacher account."""

    email = data.email.strip().lower()
    full_name = data.full_name.strip()

    if not email or not full_name:
        raise HTTPException(
            status_code=400,
            detail="email and full_name are required"
        )

    if "@" not in email:
        raise HTTPException(
            status_code=400,
            detail="email is invalid"
        )

    result = upsert_teacher(email, full_name, data.teacher_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Teacher not found"
        )

    if result.get("blocked"):
        raise HTTPException(
            status_code=409,
            detail="Teacher email already exists"
        )

    return result


@router.post("/admin/teachers/{teacher_id}/deactivate")
def deactivate_admin_teacher(teacher_id: int, current_user=Depends(require_admin_user)):
    """Archive a teacher when no active classes depend on them."""

    result = deactivate_teacher(teacher_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Active teacher not found"
        )

    if result.get("blocked"):
        raise HTTPException(
            status_code=409,
            detail="Teacher has active classes"
        )

    return result


@router.post("/admin/teachers/{teacher_id}/restore")
def restore_admin_teacher(teacher_id: int, current_user=Depends(require_admin_user)):
    """Restore an archived teacher."""

    result = restore_teacher(teacher_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Archived teacher not found"
        )

    return result


@router.post("/teacher/import-students")
async def import_teacher_students(
    school: str = Form(...),
    grade: int = Form(...),
    class_group: str = Form(...),
    task_class_id: str = Form(...),
    teacher_id: int | None = Form(default=None),
    file: UploadFile = File(...),
    current_user=Depends(require_teacher_user),
):
    """Import students from a CSV file with full_name and email columns."""

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported"
        )

    school = school.strip()

    if not active_school_exists(school):
        raise HTTPException(
            status_code=400,
            detail="School is not available"
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
    scope_id = teacher_scope_id(current_user)

    if current_user["role"] == "admin":
        if teacher_id is None:
            raise HTTPException(
                status_code=400,
                detail="teacher_id is required for admin imports"
            )

        teacher = get_active_teacher(teacher_id)

        if teacher is None:
            raise HTTPException(
                status_code=400,
                detail="Teacher is not available"
            )

        scope_id = teacher["id"]

    class_record = ensure_teacher_class(
        scope_id,
        school,
        grade,
        class_group,
        task_class_id,
    )

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
            school=school,
            grade=grade,
            class_group=class_group.strip(),
            task_class_id=task_class_id.strip(),
            teacher_id=scope_id,
            class_id=class_record["id"],
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
def upsert_teacher_student(
    data: StudentCreateRequest,
    current_user=Depends(require_teacher_user),
):
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

    school = data.school.strip()

    if not active_school_exists(school):
        raise HTTPException(
            status_code=400,
            detail="School is not available"
        )

    task_class_id = (
        data.task_class_id.strip()
        if data.task_class_id
        else f"{data.grade}class"
    )
    scope_id = teacher_scope_id(current_user)
    class_record = ensure_teacher_class(
        scope_id,
        school,
        data.grade,
        data.class_group,
        task_class_id,
    )

    student = upsert_student_by_email(
        email=data.email,
        full_name=data.full_name.strip(),
        school=school,
        grade=data.grade,
        class_group=data.class_group.strip(),
        task_class_id=task_class_id,
        teacher_id=scope_id,
        class_id=class_record["id"],
    )

    return student


@router.post("/teacher/students/{student_id}/deactivate")
def deactivate_teacher_student(
    student_id: int,
    current_user=Depends(require_teacher_user),
):
    """Hide one student from teacher journals without deleting history."""

    result = deactivate_student(student_id, teacher_scope_id(current_user))

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Active student not found"
        )

    return result


@router.post("/teacher/progress")
def override_teacher_progress(
    data: TeacherProgressOverrideRequest,
    current_user=Depends(require_teacher_user),
):
    """Manually set whether a student's task is passed from the teacher journal."""

    student = get_student(data.student_id)

    if student is None or student["is_active"] != 1:
        raise HTTPException(
            status_code=404,
            detail="Active student not found"
        )

    scope_id = teacher_scope_id(current_user)

    if scope_id is not None and student["teacher_id"] != scope_id:
        raise HTTPException(
            status_code=403,
            detail="This student is not assigned to the selected teacher"
        )

    if data.teacher_class_id is not None:
        class_record = get_teacher_class(data.teacher_class_id, scope_id)

        if class_record is None:
            raise HTTPException(
                status_code=404,
                detail="Teacher class not found"
            )

        if student["class_id"] != class_record["id"]:
            raise HTTPException(
                status_code=403,
                detail="This student is not assigned to the selected class"
            )

        if data.class_id != class_record["task_class_id"]:
            raise HTTPException(
                status_code=403,
                detail="This task base is not available for the selected class"
            )

    elif data.class_id != allowed_task_class_id(student):
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


def build_teacher_journal(
    school,
    grade,
    class_group,
    class_id,
    current_user,
    teacher_class_id=None,
):
    """Build the teacher journal data shared by JSON and CSV responses."""

    scope_id = teacher_scope_id(current_user)
    class_record = None

    if teacher_class_id is not None:
        class_record = get_teacher_class(teacher_class_id, scope_id)

        if class_record is None:
            raise HTTPException(
                status_code=404,
                detail="Teacher class not found"
            )

        school = class_record["school"]
        grade = class_record["grade"]
        class_group = class_record["class_group"]
        class_id = class_record["task_class_id"]

    if school is None or grade is None or class_group is None or class_id is None:
        raise HTTPException(
            status_code=400,
            detail="school, grade, class_group and class_id are required"
        )

    normalized_group = class_group.strip()
    all_students = list_students_with_summary(scope_id)

    if teacher_class_id is not None:
        students = [
            student
            for student in all_students
            if student["class_id"] == teacher_class_id
        ]
    else:
        students = [
            student
            for student in all_students
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
        "class": class_record,
        "students": students,
        "tasks": task_refs,
        "progress": progress,
    }


@router.get("/teacher/journal")
def get_teacher_journal(
    school: str | None = None,
    grade: int | None = None,
    class_group: str | None = None,
    class_id: str | None = None,
    teacher_class_id: int | None = None,
    current_user=Depends(require_teacher_user),
):
    """Return a teacher journal: one row per student and one column per task."""

    return build_teacher_journal(
        school,
        grade,
        class_group,
        class_id,
        current_user,
        teacher_class_id=teacher_class_id,
    )


@router.get("/teacher/journal/export")
def export_teacher_journal(
    school: str | None = None,
    grade: int | None = None,
    class_group: str | None = None,
    class_id: str | None = None,
    teacher_class_id: int | None = None,
    current_user=Depends(require_teacher_user),
):
    """Download the current teacher journal as CSV with pass statuses only."""

    journal = build_teacher_journal(
        school,
        grade,
        class_group,
        class_id,
        current_user,
        teacher_class_id=teacher_class_id,
    )

    progress_by_cell = {
        (
            progress["student_id"],
            progress["chapter"],
            progress["topic"],
            progress["number"]
        ): progress
        for progress in journal["progress"]
    }

    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    task_headers = [
        f"{task['chapter']}.{task['topic']}.{task['number']}"
        for task in journal["tasks"]
    ]

    writer.writerow([
        "ФИО",
        "email",
        "школа",
        "класс",
        *task_headers,
    ])

    for student in journal["students"]:
        row = [
            student["full_name"],
            student["email"] or "",
            student["school"],
            student["class_name"],
        ]

        for task in journal["tasks"]:
            progress = progress_by_cell.get((
                student["id"],
                task["chapter"],
                task["topic"],
                task["number"]
            ))
            row.append("1" if progress and progress["is_passed"] == 1 else "0")

        writer.writerow(row)

    export_class = journal["class"] or {
        "school": school,
        "grade": grade,
        "class_group": class_group,
        "task_class_id": class_id,
    }
    safe_group = (export_class["class_group"] or "").strip() or "class"
    filename = (
        f"journal-{export_class['school']}-{export_class['grade']}-"
        f"{safe_group}-{export_class['task_class_id']}.csv"
    )
    quoted_filename = quote(filename.replace('"', ""))

    return Response(
        "\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                "attachment; filename=\"journal.csv\"; "
                f"filename*=UTF-8''{quoted_filename}"
            )
        },
    )


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
            "teacher_override": (
                progress["teacher_override"]
                if progress
                else None
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
            "teacher_override": (
                progress["teacher_override"]
                if progress
                else None
            ),
            "updated_at": (
                progress["updated_at"]
                if progress
                else None
            )
        })

    return result
