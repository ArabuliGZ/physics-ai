"""Create stable test student logins for every available task base."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sqlite3
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.database import DATABASE_PATH
from app.database import init_database


TASKS_DIR = PROJECT_ROOT / "tasks"
TEST_SCHOOL = "Тестовая школа"
TEST_CLASS_GROUP = "test"


def main():
    """Create or update test accounts without clearing existing data."""

    init_database()
    class_ids = load_task_class_ids()

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        teacher_id = get_test_teacher_id(connection)

        for class_id in class_ids:
            student = upsert_test_student(connection, class_id, teacher_id)
            print(
                f"{student['email']} -> "
                f"{student['full_name']}, "
                f"{student['class_name']}, "
                f"{student['task_class_id']}"
            )


def load_task_class_ids():
    """Read task base ids directly from task JSON files."""

    class_ids = set()

    for path in TASKS_DIR.glob("*class.json"):
        with path.open("r", encoding="utf-8") as file:
            tasks = json.load(file)

        for task in tasks:
            class_ids.add(task["class_id"])

    return sorted(class_ids, key=class_sort_key)


def get_test_teacher_id(connection):
    """Return the local test teacher id created by database initialization."""

    row = connection.execute(
        """
        SELECT id
        FROM users
        WHERE email = 'teacher@test.ru'
        """
    ).fetchone()

    if row is None:
        raise RuntimeError("teacher@test.ru user is missing")

    return row["id"]


def upsert_test_student(connection, class_id, teacher_id):
    """Create one active test student for a task base."""

    grade = grade_from_class_id(class_id)
    email = test_email(class_id, grade)
    class_name = f"{grade}-test" if grade is not None else class_id
    full_name = f"Тестовый ученик {class_id}"

    existing = connection.execute(
        """
        SELECT id
        FROM students
        WHERE lower(email) = ?
        ORDER BY id
        LIMIT 1
        """,
        (email,),
    ).fetchone()

    if existing is None:
        cursor = connection.execute(
            """
            INSERT INTO students (
                email,
                teacher_id,
                school,
                class_name,
                grade,
                class_group,
                task_class_id,
                is_active,
                full_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                email,
                teacher_id,
                TEST_SCHOOL,
                class_name,
                grade,
                TEST_CLASS_GROUP,
                class_id,
                full_name,
            ),
        )
        student_id = cursor.lastrowid
    else:
        student_id = existing["id"]
        connection.execute(
            """
            UPDATE students
            SET school = ?,
                teacher_id = ?,
                class_name = ?,
                grade = ?,
                class_group = ?,
                task_class_id = ?,
                is_active = 1,
                full_name = ?
            WHERE id = ?
            """,
            (
                TEST_SCHOOL,
                teacher_id,
                class_name,
                grade,
                TEST_CLASS_GROUP,
                class_id,
                full_name,
                student_id,
            ),
        )

    return connection.execute(
        """
        SELECT email, full_name, class_name, task_class_id
        FROM students
        WHERE id = ?
        """,
        (student_id,),
    ).fetchone()


def grade_from_class_id(class_id):
    """Extract leading grade number from ids like 7class or 8classProf."""

    match = re.match(r"^(\d+)", class_id)

    if match is None:
        return None

    return int(match.group(1))


def test_email(class_id, grade):
    """Return a short stable login email for a test student."""

    if class_id == f"{grade}class":
        return f"{grade}@test.ru"

    safe_class_id = re.sub(r"[^a-zA-Z0-9]+", "", class_id).lower()
    return f"{safe_class_id}@test.ru"


def class_sort_key(class_id):
    """Sort class ids by leading grade, then by full id."""

    grade = grade_from_class_id(class_id)

    return (
        grade if grade is not None else 999,
        class_id,
    )


if __name__ == "__main__":
    main()
