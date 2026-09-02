"""Optional demo data seed for temporary public test stands."""

from __future__ import annotations

import random
import json
from pathlib import Path

from app.database import database_connection
from app.database import DEFAULT_TEST_PASSWORD
from app.security import hash_password


DEMO_SCHOOL = "\u0422\u0435\u0441\u0442\u043e\u0432\u0430\u044f \u0448\u043a\u043e\u043b\u0430"
DEMO_CLASS_GROUP = "demo"
DEMO_ADVANCED_CLASS_GROUP = "demo-ugl"
STUDENTS_PER_GRADE = 12
DEMO_TASK_CLASSES = (
    (7, "7class", "7", DEMO_CLASS_GROUP, "7"),
    (8, "8class", "8", DEMO_CLASS_GROUP, "8"),
    (9, "9class", "9", DEMO_CLASS_GROUP, "9"),
    (10, "10class", "10", DEMO_CLASS_GROUP, "10"),
    (11, "11class", "11", DEMO_CLASS_GROUP, "11"),
    (11, "11Uclass", "11y", DEMO_ADVANCED_CLASS_GROUP, "11У"),
)


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

        for grade, class_id, email_prefix, class_group, student_label in DEMO_TASK_CLASSES:
            tasks = tasks_by_class.get(class_id, [])

            for index in range(1, STUDENTS_PER_GRADE + 1):
                email = demo_email(email_prefix, index)
                student_id, action = upsert_demo_student(
                    connection,
                    email,
                    teacher_id,
                    grade,
                    class_id,
                    class_group,
                    student_label,
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


def reset_demo_passwords():
    """Reset public demo accounts to the shared temporary password."""

    password_hash = hash_password(DEFAULT_TEST_PASSWORD)
    demo_user_emails = ("teacher@test.ru",)
    demo_student_emails = [
        demo_email(email_prefix, index)
        for _grade, _class_id, email_prefix, _class_group, _student_label
        in DEMO_TASK_CLASSES
        for index in range(1, STUDENTS_PER_GRADE + 1)
    ]

    with database_connection() as connection:
        users_updated = connection.execute(
            f"""
            UPDATE users
            SET password_hash = ?,
                must_change_password = 0
            WHERE lower(email) IN ({",".join("?" for _ in demo_user_emails)})
            """,
            (password_hash, *demo_user_emails),
        ).rowcount

        students_updated = connection.execute(
            f"""
            UPDATE students
            SET password_hash = ?,
                must_change_password = 0
            WHERE lower(email) IN ({",".join("?" for _ in demo_student_emails)})
            """,
            (password_hash, *demo_student_emails),
        ).rowcount

    return {
        "users_updated": users_updated,
        "students_updated": students_updated,
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
    """Create or reactivate the demo teacher account."""

    password_hash = hash_password(DEFAULT_TEST_PASSWORD)

    connection.execute(
        """
        INSERT INTO users (email, password_hash, must_change_password, role, full_name, is_active)
        VALUES (?, ?, 0, ?, ?, 1)
        ON CONFLICT(email) DO UPDATE SET
            password_hash = excluded.password_hash,
            must_change_password = 0,
            role = excluded.role,
            full_name = excluded.full_name,
            is_active = 1
        """,
        (email, password_hash, role, full_name),
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


def demo_email(prefix, index):
    """Return short grade logins plus numbered classmates."""

    if index == 1:
        return f"{prefix}@test.ru"

    return f"{prefix}-demo-{index:02d}@test.ru"


def upsert_demo_student(
    connection,
    email,
    teacher_id,
    grade,
    class_id,
    class_group,
    student_label,
    index,
):
    """Create or update one demo student."""

    password_hash = hash_password(DEFAULT_TEST_PASSWORD)
    class_name = f"{grade}-{class_group}"
    full_name = (
        f"\u0422\u0435\u0441\u0442\u043e\u0432\u044b\u0439 "
        f"\u0443\u0447\u0435\u043d\u0438\u043a {student_label}.{index:02d}"
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
                password_hash,
                must_change_password,
                teacher_id,
                school,
                class_name,
                grade,
                class_group,
                task_class_id,
                is_active,
                full_name
            )
            VALUES (?, ?, 0, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                email,
                password_hash,
                teacher_id,
                DEMO_SCHOOL,
                class_name,
                grade,
                class_group,
                class_id,
                full_name,
            ),
        )

        return cursor.lastrowid, "created"

    connection.execute(
        """
        UPDATE students
        SET teacher_id = ?,
            password_hash = ?,
            must_change_password = 0,
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
            password_hash,
            DEMO_SCHOOL,
            class_name,
            grade,
            class_group,
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
