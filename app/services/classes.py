"""Helpers for teacher class records."""

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
    """Return active classes visible to a teacher or admin."""

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
                COALESCE(student_summary.students_count, 0) AS students_count
            FROM classes
            LEFT JOIN (
                SELECT class_id, COUNT(*) AS students_count
                FROM students
                WHERE is_active = 1
                GROUP BY class_id
            ) AS student_summary
                ON student_summary.class_id = classes.id
            WHERE classes.is_active = 1
              {teacher_clause}
            ORDER BY classes.school, classes.grade, classes.class_group, classes.task_class_id
            """,
            params,
        ).fetchall()

        return [row_to_dict(row) for row in rows]
