"""Helpers for teacher/admin login sessions."""

import secrets

from app.database import database_connection


def row_to_dict(row):
    """Convert sqlite3.Row to a regular dict."""

    if row is None:
        return None

    return dict(row)


def create_user_session(user_id):
    """Create a random session token for a logged-in teacher/admin."""

    token = secrets.token_urlsafe(32)

    with database_connection() as connection:
        connection.execute(
            """
            INSERT INTO user_sessions (token, user_id)
            VALUES (?, ?)
            """,
            (token, user_id),
        )

    return token


def find_user_by_session_token(token):
    """Return an active teacher/admin user for a session token."""

    if not token:
        return None

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT
                users.id,
                users.email,
                users.role,
                users.full_name,
                users.is_active,
                users.created_at
            FROM user_sessions
            JOIN users
                ON users.id = user_sessions.user_id
            WHERE user_sessions.token = ?
              AND users.is_active = 1
              AND users.role IN ('teacher', 'admin')
            LIMIT 1
            """,
            (token,),
        ).fetchone()

        return row_to_dict(row)


def delete_user_session(token):
    """Remove one session token during logout."""

    if not token:
        return

    with database_connection() as connection:
        connection.execute(
            """
            DELETE FROM user_sessions
            WHERE token = ?
            """,
            (token,),
        )


def create_student_session(student_id):
    """Create a random session token for a logged-in student."""

    token = secrets.token_urlsafe(32)

    with database_connection() as connection:
        connection.execute(
            """
            INSERT INTO student_sessions (token, student_id)
            VALUES (?, ?)
            """,
            (token, student_id),
        )

    return token


def find_student_by_session_token(token):
    """Return an active student for a session token."""

    if not token:
        return None

    with database_connection() as connection:
        row = connection.execute(
            """
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
                students.created_at
            FROM student_sessions
            JOIN students
                ON students.id = student_sessions.student_id
            WHERE student_sessions.token = ?
              AND students.is_active = 1
            LIMIT 1
            """,
            (token,),
        ).fetchone()

        return row_to_dict(row)


def delete_student_session(token):
    """Remove one student session token during logout."""

    if not token:
        return

    with database_connection() as connection:
        connection.execute(
            """
            DELETE FROM student_sessions
            WHERE token = ?
            """,
            (token,),
        )
