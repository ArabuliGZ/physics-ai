"""Helpers for task attempts and current student progress."""

from app.database import database_connection


def row_to_dict(row):
    """Convert sqlite3.Row to a regular dict for API-friendly use."""

    if row is None:
        return None

    return dict(row)


def record_task_attempt(
    student_id,
    class_id,
    chapter,
    topic,
    number,
    solution_text,
    ai_response=None,
    is_passed=False,
):
    """Save one attempt and update the student's current task progress."""

    passed_value = 1 if is_passed else 0

    with database_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO task_attempts (
                student_id,
                class_id,
                chapter,
                topic,
                number,
                solution_text,
                ai_response,
                is_passed
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                student_id,
                class_id,
                chapter,
                topic,
                number,
                solution_text,
                ai_response,
                passed_value,
            ),
        )

        connection.execute(
            """
            INSERT INTO task_progress (
                student_id,
                class_id,
                chapter,
                topic,
                number,
                attempts_count,
                is_passed,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, 1, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (student_id, class_id, chapter, topic, number)
            DO UPDATE SET
                attempts_count = attempts_count + 1,
                is_passed = MAX(is_passed, excluded.is_passed),
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                student_id,
                class_id,
                chapter,
                topic,
                number,
                passed_value,
            ),
        )

        attempt_id = cursor.lastrowid

        row = connection.execute(
            """
            SELECT id, student_id, class_id, chapter, topic, number,
                   solution_text, ai_response, is_passed, created_at
            FROM task_attempts
            WHERE id = ?
            """,
            (attempt_id,),
        ).fetchone()

        return row_to_dict(row)


def get_task_progress(student_id, class_id, chapter, topic, number):
    """Return current progress for one student and task."""

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT id, student_id, class_id, chapter, topic, number,
                   attempts_count, is_passed, updated_at
            FROM task_progress
            WHERE student_id = ?
              AND class_id = ?
              AND chapter = ?
              AND topic = ?
              AND number = ?
            """,
            (student_id, class_id, chapter, topic, number),
        ).fetchone()

        return row_to_dict(row)


def list_student_progress(student_id):
    """Return all progress rows for one student."""

    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, student_id, class_id, chapter, topic, number,
                   attempts_count, is_passed, updated_at
            FROM task_progress
            WHERE student_id = ?
            ORDER BY class_id, chapter, topic, number
            """,
            (student_id,),
        ).fetchall()

        return [row_to_dict(row) for row in rows]


def get_progress_map(student_id, class_id, chapter, topic):
    """Return progress rows keyed by task number for one section."""

    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT number, attempts_count, is_passed, updated_at
            FROM task_progress
            WHERE student_id = ?
              AND class_id = ?
              AND chapter = ?
              AND topic = ?
            """,
            (student_id, class_id, chapter, topic),
        ).fetchall()

        return {
            row["number"]: row_to_dict(row)
            for row in rows
        }


def get_class_progress_map(student_id, class_id):
    """Return progress rows keyed by chapter, topic and task number."""

    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT chapter, topic, number, attempts_count, is_passed, updated_at
            FROM task_progress
            WHERE student_id = ?
              AND class_id = ?
            """,
            (student_id, class_id),
        ).fetchall()

        return {
            (
                row["chapter"],
                row["topic"],
                row["number"]
            ): row_to_dict(row)
            for row in rows
        }


def list_teacher_journal_progress(student_ids, class_id):
    """Return progress rows for many students in one task base."""

    if not student_ids:
        return []

    placeholders = ", ".join("?" for _ in student_ids)

    with database_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT student_id, class_id, chapter, topic, number,
                   attempts_count, is_passed, updated_at
            FROM task_progress
            WHERE class_id = ?
              AND student_id IN ({placeholders})
            """,
            (class_id, *student_ids),
        ).fetchall()

        return [row_to_dict(row) for row in rows]


def list_task_attempts(student_id, class_id, chapter, topic, number):
    """Return attempt history for one student and task."""

    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, student_id, class_id, chapter, topic, number,
                   solution_text, ai_response, is_passed, created_at
            FROM task_attempts
            WHERE student_id = ?
              AND class_id = ?
              AND chapter = ?
              AND topic = ?
              AND number = ?
            ORDER BY created_at, id
            """,
            (student_id, class_id, chapter, topic, number),
        ).fetchall()

        return [row_to_dict(row) for row in rows]
