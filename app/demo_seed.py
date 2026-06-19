"""Optional demo data seed for temporary public test stands."""

from __future__ import annotations

import random
import json
from pathlib import Path

from app.database import database_connection


DEMO_SCHOOL = "\u0422\u0435\u0441\u0442\u043e\u0432\u0430\u044f \u0448\u043a\u043e\u043b\u0430"
DEMO_CLASS_GROUP = "demo"
STUDENTS_PER_GRADE = 12
GRADES = (7, 8, 9)


def seed_demo_data():
    """Create stable demo users, students and progress without deleting data."""

    random.seed(42)

    tasks_by_class = group_tasks_by_class()
    students_created = 0
    students_updated = 0
    progress_created = 0

    with database_connection() as connection:
        teacher_id = ensure_demo_user(
            connection,
            "teacher@test.ru",
            "teacher",
            "\u0422\u0435\u0441\u0442\u043e\u0432\u044b\u0439 \u0443\u0447\u0438\u0442\u0435\u043b\u044c",
        )
        ensure_demo_user(
            connection,
            "admin@test.ru",
            "admin",
            "\u0410\u0434\u043c\u0438\u043d\u0438\u0441\u0442\u0440\u0430\u0442\u043e\u0440",
        )

        for grade in GRADES:
            class_id = f"{grade}class"
            tasks = tasks_by_class.get(class_id, [])

            for index in range(1, STUDENTS_PER_GRADE + 1):
                email = demo_email(grade, index)
                student_id, action = upsert_demo_student(
                    connection,
                    email,
                    teacher_id,
                    grade,
                    class_id,
                    index,
                )

                if action == "created":
                    students_created += 1
                else:
                    students_updated += 1

                progress_created += seed_demo_progress(
                    connection,
                    student_id,
                    class_id,
                    tasks,
                    index,
                )

    return {
        "students_created": students_created,
        "students_updated": students_updated,
        "progress_created": progress_created,
    }


def group_tasks_by_class():
    """Group task metadata by class id."""

    tasks_by_class = {}

    for path in Path("tasks").glob("*class.json"):
        with path.open("r", encoding="utf-8") as file:
            tasks = json.load(file)

        for task in tasks:
            tasks_by_class.setdefault(task["class_id"], []).append(task)

    for tasks in tasks_by_class.values():
        tasks.sort(key=lambda task: (
            int(task["chapter"]),
            int(task["topic"]),
            int(task["number"]),
        ))

    return tasks_by_class


def ensure_demo_user(connection, email, role, full_name):
    """Create or reactivate one demo teacher/admin account."""

    connection.execute(
        """
        INSERT INTO users (email, role, full_name, is_active)
        VALUES (?, ?, ?, 1)
        ON CONFLICT(email) DO UPDATE SET
            role = excluded.role,
            full_name = excluded.full_name,
            is_active = 1
        """,
        (email, role, full_name),
    )

    row = connection.execute(
        """
        SELECT id
        FROM users
        WHERE email = ?
        """,
        (email,),
    ).fetchone()

    return row["id"]


def demo_email(grade, index):
    """Return short grade logins plus numbered classmates."""

    if index == 1:
        return f"{grade}@test.ru"

    return f"{grade}-demo-{index:02d}@test.ru"


def upsert_demo_student(connection, email, teacher_id, grade, class_id, index):
    """Create or update one demo student."""

    class_name = f"{grade}-demo"
    full_name = (
        f"\u0422\u0435\u0441\u0442\u043e\u0432\u044b\u0439 "
        f"\u0443\u0447\u0435\u043d\u0438\u043a {grade}.{index:02d}"
    )

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
                DEMO_SCHOOL,
                class_name,
                grade,
                DEMO_CLASS_GROUP,
                class_id,
                full_name,
            ),
        )

        return cursor.lastrowid, "created"

    connection.execute(
        """
        UPDATE students
        SET teacher_id = ?,
            school = ?,
            class_name = ?,
            grade = ?,
            class_group = ?,
            task_class_id = ?,
            is_active = 1,
            full_name = ?
        WHERE id = ?
        """,
        (
            teacher_id,
            DEMO_SCHOOL,
            class_name,
            grade,
            DEMO_CLASS_GROUP,
            class_id,
            full_name,
            existing["id"],
        ),
    )

    return existing["id"], "updated"


def seed_demo_progress(connection, student_id, class_id, tasks, student_index):
    """Create stable 0/1 progress for a subset of demo tasks."""

    if not tasks:
        return 0

    sample_size = min(36, len(tasks))
    selected_tasks = tasks[:sample_size]
    progress_created = 0

    for task_index, task in enumerate(selected_tasks, start=1):
        attempts = (student_index + task_index) % 4 + 1
        is_passed = 1 if (student_index * 3 + task_index) % 5 in (0, 1, 2) else 0

        cursor = connection.execute(
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
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (student_id, class_id, chapter, topic, number)
            DO NOTHING
            """,
            (
                student_id,
                class_id,
                task["chapter"],
                task["topic"],
                task["number"],
                attempts,
                is_passed,
            ),
        )

        progress_created += cursor.rowcount

    return progress_created
