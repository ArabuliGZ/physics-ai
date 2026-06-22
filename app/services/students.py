"""Helpers for reading and writing student records."""

import re

from app.database import database_connection
from app.database import DEFAULT_TEST_PASSWORD
from app.database import sync_student_classes
from app.security import hash_password
from app.security import verify_password


def row_to_dict(row):
    """Convert sqlite3.Row to a regular dict for API-friendly use."""

    if row is None:
        return None

    return dict(row)


def normalize_class_parts(class_name=None, grade=None, class_group=None):
    """Return grade, class group and display class name from mixed inputs."""

    parsed_grade = grade
    parsed_group = class_group

    if parsed_grade is None and class_name:
        match = re.match(r"^\s*(\d+)\s*[-\s]?\s*(.*)\s*$", class_name)

        if match:
            parsed_grade = int(match.group(1))
            parsed_group = parsed_group or match.group(2).strip() or None

    if parsed_grade is None:
        raise ValueError("grade is required")

    parsed_group = (parsed_group or "").strip() or None
    display_name = make_class_name(parsed_grade, parsed_group)

    return parsed_grade, parsed_group, display_name


def make_class_name(grade, class_group):
    """Build a readable class name while keeping school-specific group labels."""

    if class_group:
        if class_group[0].isdigit():
            return f"{grade}-{class_group}"

        return f"{grade}{class_group}"

    return str(grade)


def allowed_task_class_id(student):
    """Return the task base id that a student is allowed to use."""

    if not student:
        return None

    return student.get("task_class_id")


def create_student(
    school,
    class_name,
    full_name,
    grade=None,
    class_group=None,
    task_class_id=None,
    email=None,
    teacher_id=None,
    class_id=None,
):
    """Create a student and return the saved row."""

    grade, class_group, class_name = normalize_class_parts(
        class_name=class_name,
        grade=grade,
        class_group=class_group,
    )
    task_class_id = task_class_id or f"{grade}class"

    with database_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO students (
                school,
                class_id,
                teacher_id,
                email,
                password_hash,
                class_name,
                grade,
                class_group,
                task_class_id,
                full_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                school,
                class_id,
                teacher_id,
                email,
                hash_password(DEFAULT_TEST_PASSWORD),
                class_name,
                grade,
                class_group,
                task_class_id,
                full_name,
            ),
        )

        student_id = cursor.lastrowid

        sync_student_classes(connection)

        row = connection.execute(
            """
            SELECT id, class_id, teacher_id, email, school, class_name, grade, class_group,
                   task_class_id, is_active, full_name, created_at
            FROM students
            WHERE id = ?
            """,
            (student_id,),
        ).fetchone()

        return row_to_dict(row)


def find_student(school, class_name, full_name, grade=None, class_group=None):
    """Find a student by school, class and full name."""

    grade, class_group, class_name = normalize_class_parts(
        class_name=class_name,
        grade=grade,
        class_group=class_group,
    )

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT id, class_id, teacher_id, email, school, class_name, grade, class_group,
                   task_class_id, is_active, full_name, created_at
            FROM students
            WHERE school = ?
              AND grade = ?
              AND COALESCE(class_group, '') = COALESCE(?, '')
              AND full_name = ?
              AND is_active = 1
            ORDER BY id
            LIMIT 1
            """,
            (school, grade, class_group, full_name),
        ).fetchone()

        return row_to_dict(row)


def find_or_create_student(
    school,
    class_name,
    full_name,
    grade=None,
    class_group=None,
    task_class_id=None,
    email=None,
    teacher_id=None,
    class_id=None,
):
    """Return an existing student or create a new one."""

    student = find_student(
        school,
        class_name,
        full_name,
        grade=grade,
        class_group=class_group,
    )

    if student is not None:
        return student

    return create_student(
        school,
        class_name,
        full_name,
        grade=grade,
        class_group=class_group,
        task_class_id=task_class_id,
        email=email,
        teacher_id=teacher_id,
        class_id=class_id,
    )


def find_student_by_email(email, include_inactive=False):
    """Find a student by email for login."""

    normalized_email = normalize_email(email)
    active_clause = "" if include_inactive else "AND is_active = 1"

    with database_connection() as connection:
        row = connection.execute(
            f"""
            SELECT id, class_id, teacher_id, email, school, class_name, grade, class_group,
                   task_class_id, is_active, full_name, created_at
            FROM students
            WHERE lower(email) = ?
              {active_clause}
            ORDER BY id
            LIMIT 1
            """,
            (normalized_email,),
        ).fetchone()

        return row_to_dict(row)


def authenticate_student(email, password):
    """Return an active student only when email and password match."""

    normalized_email = normalize_email(email)

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT id, class_id, teacher_id, email, password_hash, school, class_name,
                   grade, class_group, task_class_id, is_active, full_name, created_at
            FROM students
            WHERE lower(email) = ?
              AND is_active = 1
            ORDER BY id
            LIMIT 1
            """,
            (normalized_email,),
        ).fetchone()

        if row is None or not verify_password(password, row["password_hash"]):
            return None

        result = row_to_dict(row)
        result.pop("password_hash", None)
        return result


def upsert_student_by_email(
    email,
    full_name,
    school,
    grade,
    class_group,
    task_class_id,
    teacher_id=None,
    class_id=None,
):
    """Create or update a student by email and return the saved row."""

    normalized_email = normalize_email(email)
    grade, class_group, class_name = normalize_class_parts(
        grade=grade,
        class_group=class_group,
    )

    existing = find_student_by_email(
        normalized_email,
        include_inactive=True,
    )

    with database_connection() as connection:
        if existing is None:
            cursor = connection.execute(
                """
                INSERT INTO students (
                    email,
                    password_hash,
                    class_id,
                    teacher_id,
                    school,
                    class_name,
                    grade,
                    class_group,
                    task_class_id,
                    full_name
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized_email,
                    hash_password(DEFAULT_TEST_PASSWORD),
                    class_id,
                    teacher_id,
                    school,
                    class_name,
                    grade,
                    class_group,
                    task_class_id,
                    full_name,
                ),
            )
            student_id = cursor.lastrowid
            action = "created"
        else:
            student_id = existing["id"]
            connection.execute(
                """
                UPDATE students
                SET email = ?,
                    class_id = ?,
                    teacher_id = ?,
                    school = ?,
                    class_name = ?,
                    grade = ?,
                    class_group = ?,
                    task_class_id = ?,
                    full_name = ?,
                    is_active = 1,
                    hidden_by_class_archive = 0
                WHERE id = ?
                """,
                (
                    normalized_email,
                    class_id if class_id is not None else existing["class_id"],
                    teacher_id if teacher_id is not None else existing["teacher_id"],
                    school,
                    class_name,
                    grade,
                    class_group,
                    task_class_id,
                    full_name,
                    student_id,
                ),
            )
            action = "updated"

        sync_student_classes(connection)

        row = connection.execute(
            """
            SELECT id, class_id, teacher_id, email, school, class_name, grade, class_group,
                   task_class_id, is_active, full_name, created_at
            FROM students
            WHERE id = ?
            """,
            (student_id,),
        ).fetchone()

        result = row_to_dict(row)
        result["action"] = action

        return result


def get_student(student_id):
    """Return one student by id, or None if the id is unknown."""

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT id, class_id, teacher_id, email, school, class_name, grade, class_group,
                   task_class_id, is_active, full_name, created_at
            FROM students
            WHERE id = ?
            """,
            (student_id,),
        ).fetchone()

        return row_to_dict(row)


def list_students(teacher_id=None):
    """Return all students ordered for a teacher-friendly overview."""

    teacher_clause = ""
    params = ()

    if teacher_id is not None:
        teacher_clause = "AND teacher_id = ?"
        params = (teacher_id,)

    with database_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT id, class_id, teacher_id, email, school, class_name, grade, class_group,
                   task_class_id, is_active, full_name, created_at
            FROM students
            WHERE is_active = 1
              {teacher_clause}
            ORDER BY school, grade, class_group, full_name, id
            """,
            params,
        ).fetchall()

        return [row_to_dict(row) for row in rows]


def list_students_with_summary(teacher_id=None):
    """Return students with progress totals for the teacher overview."""

    teacher_clause = ""
    params = ()

    if teacher_id is not None:
        teacher_clause = "AND students.teacher_id = ?"
        params = (teacher_id,)

    with database_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT
                students.id,
                students.class_id,
                students.teacher_id,
                students.email,
                students.school,
                students.class_name,
                students.grade,
                students.class_group,
                students.task_class_id,
                students.is_active,
                students.full_name,
                students.created_at,
                COALESCE(summary.total_attempts, 0) AS total_attempts,
                COALESCE(summary.tried_tasks, 0) AS tried_tasks,
                COALESCE(summary.passed_tasks, 0) AS passed_tasks,
                summary.last_activity
            FROM students
            LEFT JOIN (
                SELECT
                    student_id,
                    SUM(attempts_count) AS total_attempts,
                    COUNT(*) AS tried_tasks,
                    SUM(is_passed) AS passed_tasks,
                    MAX(updated_at) AS last_activity
                FROM task_progress
                GROUP BY student_id
            ) AS summary
                ON summary.student_id = students.id
            WHERE students.is_active = 1
              {teacher_clause}
            ORDER BY students.school, students.grade, students.class_group, students.full_name, students.id
            """,
            params,
        ).fetchall()

        return [row_to_dict(row) for row in rows]


def normalize_email(email):
    """Normalize an email address for stable lookup."""

    return (email or "").strip().lower()


def deactivate_student(student_id, teacher_id=None):
    """Hide a student from teacher journals while keeping history."""

    teacher_clause = ""
    params = [student_id]

    if teacher_id is not None:
        teacher_clause = "AND teacher_id = ?"
        params.append(teacher_id)

    with database_connection() as connection:
        row = connection.execute(
            f"""
            SELECT id
            FROM students
            WHERE id = ?
              AND is_active = 1
              {teacher_clause}
            """,
            params,
        ).fetchone()

        if row is None:
            return None

        connection.execute(
            """
            UPDATE students
            SET is_active = 0
            WHERE id = ?
            """,
            (student_id,),
        )

        return {
            "id": student_id,
            "is_active": 0,
        }
