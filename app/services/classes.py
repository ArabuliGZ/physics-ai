"""Helpers for teacher class records."""

import sqlite3

from app.database import database_connection
from app.database import ensure_class_row


def row_to_dict(row):
    """Convert sqlite3.Row to a regular dict."""

    if row is None:
        return None

    return dict(row)


def make_class_name(grade, class_group):
    """Build the class display name from grade and school-specific group label."""

    if class_group:
        if class_group[0].isdigit():
            return f"{grade}-{class_group}"

        return f"{grade}{class_group}"

    return str(grade)


def ensure_teacher_class(
    teacher_id,
    school,
    grade,
    class_group,
    task_class_id,
):
    """Create or reactivate a teacher class and return the saved row."""

    school = school.strip()
    class_group = (class_group or "").strip()
    task_class_id = task_class_id.strip()
    class_name = make_class_name(grade, class_group)

    with database_connection() as connection:
        class_id = ensure_class_row(
            connection,
            teacher_id,
            school,
            grade,
            class_group,
            class_name,
            task_class_id,
        )

        row = connection.execute(
            """
            SELECT
                id,
                teacher_id,
                school,
                grade,
                class_group,
                class_name,
                task_class_id,
                is_active,
                created_at
            FROM classes
            WHERE id = ?
            """,
            (class_id,),
        ).fetchone()

        return row_to_dict(row)


def get_teacher_class(class_id, teacher_id=None):
    """Return one class visible to the current teacher or admin."""

    teacher_clause = ""
    params = [class_id]

    if teacher_id is not None:
        teacher_clause = "AND teacher_id = ?"
        params.append(teacher_id)

    with database_connection() as connection:
        row = connection.execute(
            f"""
            SELECT
                id,
                teacher_id,
                school,
                grade,
                class_group,
                class_name,
                task_class_id,
                is_active,
                created_at
            FROM classes
            WHERE id = ?
              AND is_active = 1
              {teacher_clause}
            LIMIT 1
            """,
            params,
        ).fetchone()

        return row_to_dict(row)


def list_teacher_classes(teacher_id=None):
    """Return active and archived classes visible to a teacher or admin."""

    teacher_clause = ""
    params = ()

    if teacher_id is not None:
        teacher_clause = "AND classes.teacher_id = ?"
        params = (teacher_id,)

    with database_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT
                classes.id,
                classes.teacher_id,
                classes.school,
                classes.grade,
                classes.class_group,
                classes.class_name,
                classes.task_class_id,
                classes.is_active,
                classes.created_at,
                CASE
                    WHEN classes.is_active = 1
                    THEN COALESCE(student_summary.active_students, 0)
                    ELSE COALESCE(classes.archived_students_count, 0)
                END AS students_count
            FROM classes
            LEFT JOIN (
                SELECT class_id, COUNT(*) AS active_students
                FROM students
                WHERE is_active = 1
                GROUP BY class_id
            ) AS student_summary
                ON student_summary.class_id = classes.id
            WHERE 1 = 1
              {teacher_clause}
            ORDER BY classes.is_active DESC,
                     classes.school,
                     classes.grade,
                     classes.class_group,
                     classes.task_class_id
            """,
            params,
        ).fetchall()

        return [row_to_dict(row) for row in rows]


def deactivate_teacher_class(class_id, teacher_id=None):
    """Archive one class and hide its active students while preserving history."""

    teacher_clause = ""
    params = [class_id]

    if teacher_id is not None:
        teacher_clause = "AND teacher_id = ?"
        params.append(teacher_id)

    with database_connection() as connection:
        row = connection.execute(
            f"""
            SELECT id
            FROM classes
            WHERE id = ?
              AND is_active = 1
              {teacher_clause}
            LIMIT 1
            """,
            params,
        ).fetchone()

        if row is None:
            return None

        active_students = connection.execute(
            """
            SELECT COUNT(*) AS students_count
            FROM students
            WHERE class_id = ?
              AND is_active = 1
            """,
            (class_id,),
        ).fetchone()["students_count"]

        connection.execute(
            """
            UPDATE classes
            SET is_active = 0,
                archived_students_count = ?
            WHERE id = ?
            """,
            (active_students, class_id),
        )
        connection.execute(
            """
            UPDATE students
            SET is_active = 0,
                hidden_by_class_archive = 1
            WHERE class_id = ?
              AND is_active = 1
            """,
            (class_id,),
        )

        return {
            "id": class_id,
            "is_active": 0,
        }


def list_admin_classes():
    """Return all classes with teacher and active student counters."""

    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                classes.id,
                classes.teacher_id,
                users.full_name AS teacher_name,
                users.email AS teacher_email,
                classes.school,
                classes.grade,
                classes.class_group,
                classes.class_name,
                classes.task_class_id,
                classes.is_active,
                classes.created_at,
                CASE
                    WHEN classes.is_active = 1
                    THEN COALESCE(student_summary.active_students, 0)
                    ELSE COALESCE(classes.archived_students_count, 0)
                END AS active_students
            FROM classes
            LEFT JOIN users
                ON users.id = classes.teacher_id
            LEFT JOIN (
                SELECT class_id, COUNT(*) AS active_students
                FROM students
                WHERE is_active = 1
                GROUP BY class_id
            ) AS student_summary
                ON student_summary.class_id = classes.id
            ORDER BY classes.is_active DESC,
                     classes.school,
                     classes.grade,
                     classes.class_group,
                     classes.task_class_id
            """
        ).fetchall()

        return [row_to_dict(row) for row in rows]


def restore_teacher_class(class_id, teacher_id=None):
    """Reactivate an archived class and its students."""

    teacher_clause = ""
    params = [class_id]

    if teacher_id is not None:
        teacher_clause = "AND teacher_id = ?"
        params.append(teacher_id)

    with database_connection() as connection:
        row = connection.execute(
            f"""
            SELECT id
            FROM classes
            WHERE id = ?
              AND is_active = 0
              {teacher_clause}
            LIMIT 1
            """,
            params,
        ).fetchone()

        if row is None:
            return None

        connection.execute(
            """
            UPDATE classes
            SET is_active = 1,
                archived_students_count = NULL
            WHERE id = ?
            """,
            (class_id,),
        )
        connection.execute(
            """
            UPDATE students
            SET is_active = 1,
                hidden_by_class_archive = 0
            WHERE class_id = ?
              AND hidden_by_class_archive = 1
            """,
            (class_id,),
        )

        return {
            "id": class_id,
            "is_active": 1,
        }


def update_teacher_class(
    class_id,
    school,
    grade,
    class_group,
    task_class_id,
    teacher_id=None,
    scope_teacher_id=None,
):
    """Update class metadata and keep student snapshots in sync."""

    school = school.strip()
    class_group = (class_group or "").strip()
    task_class_id = task_class_id.strip()
    class_name = make_class_name(grade, class_group)

    teacher_clause = ""
    params = [class_id]

    if scope_teacher_id is not None:
        teacher_clause = "AND teacher_id = ?"
        params.append(scope_teacher_id)

    with database_connection() as connection:
        row = connection.execute(
            f"""
            SELECT id, teacher_id
            FROM classes
            WHERE id = ?
              {teacher_clause}
            LIMIT 1
            """,
            params,
        ).fetchone()

        if row is None:
            return None

        saved_teacher_id = row["teacher_id"]

        if teacher_id is not None and int(teacher_id) != int(saved_teacher_id):
            teacher = connection.execute(
                """
                SELECT id
                FROM users
                WHERE id = ?
                  AND role = 'teacher'
                  AND is_active = 1
                LIMIT 1
                """,
                (teacher_id,),
            ).fetchone()

            if teacher is None:
                return {
                    "blocked": True,
                    "detail": "teacher_not_found",
                }

            saved_teacher_id = teacher_id

        try:
            connection.execute(
                """
                UPDATE classes
                SET teacher_id = ?,
                    school = ?,
                    grade = ?,
                    class_group = ?,
                    class_name = ?,
                    task_class_id = ?
                WHERE id = ?
                """,
                (
                    saved_teacher_id,
                    school,
                    grade,
                    class_group,
                    class_name,
                    task_class_id,
                    class_id,
                ),
            )
        except sqlite3.IntegrityError:
            return {
                "blocked": True,
                "detail": "class_already_exists",
            }

        connection.execute(
            """
            UPDATE students
            SET teacher_id = ?,
                school = ?,
                grade = ?,
                class_group = ?,
                class_name = ?,
                task_class_id = ?
            WHERE class_id = ?
            """,
            (
                saved_teacher_id,
                school,
                grade,
                class_group,
                class_name,
                task_class_id,
                class_id,
            ),
        )

        return {
            "id": class_id,
            "teacher_id": saved_teacher_id,
            "school": school,
            "grade": grade,
            "class_group": class_group,
            "class_name": class_name,
            "task_class_id": task_class_id,
        }


def update_class_teacher(class_id, teacher_id):
    """Assign a class to an active teacher without changing students or progress."""

    with database_connection() as connection:
        teacher = connection.execute(
            """
            SELECT id
            FROM users
            WHERE id = ?
              AND role = 'teacher'
              AND is_active = 1
            LIMIT 1
            """,
            (teacher_id,),
        ).fetchone()

        if teacher is None:
            return {
                "blocked": True,
                "detail": "teacher_not_found",
            }

        row = connection.execute(
            """
            SELECT id
            FROM classes
            WHERE id = ?
            LIMIT 1
            """,
            (class_id,),
        ).fetchone()

        if row is None:
            return None

        connection.execute(
            """
            UPDATE classes
            SET teacher_id = ?
            WHERE id = ?
            """,
            (teacher_id, class_id),
        )

        return {
            "id": class_id,
            "teacher_id": teacher_id,
        }
