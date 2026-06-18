"""Helpers for reading and writing student records."""

import re

from app.database import database_connection


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

    if not student or student.get("grade") is None:
        return None

    return f"{student['grade']}class"


def create_student(school, class_name, full_name, grade=None, class_group=None):
    """Create a student and return the saved row."""

    grade, class_group, class_name = normalize_class_parts(
        class_name=class_name,
        grade=grade,
        class_group=class_group,
    )

    with database_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO students (school, class_name, grade, class_group, full_name)
            VALUES (?, ?, ?, ?, ?)
            """,
            (school, class_name, grade, class_group, full_name),
        )

        student_id = cursor.lastrowid

        row = connection.execute(
            """
            SELECT id, school, class_name, grade, class_group, full_name, created_at
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
            SELECT id, school, class_name, grade, class_group, full_name, created_at
            FROM students
            WHERE school = ?
              AND grade = ?
              AND COALESCE(class_group, '') = COALESCE(?, '')
              AND full_name = ?
            ORDER BY id
            LIMIT 1
            """,
            (school, grade, class_group, full_name),
        ).fetchone()

        return row_to_dict(row)


def find_or_create_student(school, class_name, full_name, grade=None, class_group=None):
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
    )


def get_student(student_id):
    """Return one student by id, or None if the id is unknown."""

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT id, school, class_name, grade, class_group, full_name, created_at
            FROM students
            WHERE id = ?
            """,
            (student_id,),
        ).fetchone()

        return row_to_dict(row)


def list_students():
    """Return all students ordered for a teacher-friendly overview."""

    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, school, class_name, grade, class_group, full_name, created_at
            FROM students
            ORDER BY school, grade, class_group, full_name, id
            """
        ).fetchall()

        return [row_to_dict(row) for row in rows]


def list_students_with_summary():
    """Return students with progress totals for the teacher overview."""

    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                students.id,
                students.school,
                students.class_name,
                students.grade,
                students.class_group,
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
            ORDER BY students.school, students.grade, students.class_group, students.full_name, students.id
            """
        ).fetchall()

        return [row_to_dict(row) for row in rows]
