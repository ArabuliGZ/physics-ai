"""Helpers for reading and writing student records."""

from app.database import database_connection


def row_to_dict(row):
    """Convert sqlite3.Row to a regular dict for API-friendly use."""

    if row is None:
        return None

    return dict(row)


def create_student(school, class_name, full_name):
    """Create a student and return the saved row."""

    with database_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO students (school, class_name, full_name)
            VALUES (?, ?, ?)
            """,
            (school, class_name, full_name),
        )

        student_id = cursor.lastrowid

        row = connection.execute(
            """
            SELECT id, school, class_name, full_name, created_at
            FROM students
            WHERE id = ?
            """,
            (student_id,),
        ).fetchone()

        return row_to_dict(row)


def find_student(school, class_name, full_name):
    """Find a student by school, class and full name."""

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT id, school, class_name, full_name, created_at
            FROM students
            WHERE school = ?
              AND class_name = ?
              AND full_name = ?
            ORDER BY id
            LIMIT 1
            """,
            (school, class_name, full_name),
        ).fetchone()

        return row_to_dict(row)


def find_or_create_student(school, class_name, full_name):
    """Return an existing student or create a new one."""

    student = find_student(
        school,
        class_name,
        full_name
    )

    if student is not None:
        return student

    return create_student(
        school,
        class_name,
        full_name
    )


def get_student(student_id):
    """Return one student by id, or None if the id is unknown."""

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT id, school, class_name, full_name, created_at
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
            SELECT id, school, class_name, full_name, created_at
            FROM students
            ORDER BY school, class_name, full_name, id
            """
        ).fetchall()

        return [row_to_dict(row) for row in rows]
