"""Reset the local SQLite database and fill it with teacher-journal test data."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from datetime import timedelta
from pathlib import Path
import random
import shutil
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.database import DATABASE_PATH
from app.database import get_connection
from app.database import init_database
from app.services.task_store import TASKS


LETOVO = "\u041b\u0435\u0442\u043e\u0432\u043e"
L2SH = "\u041b2\u0428"
FIRST_L2SH_LETTERS = ("\u0410", "\u0411", "\u0412")
FAMILY_PREFIX = "\u0424\u0430\u043c\u0438\u043b\u0438\u044f"
NAME_PREFIX = "\u0418\u043c\u044f"

SCHOOLS = (LETOVO, L2SH)
GRADES = (7, 8, 9, 10)
STUDENTS_PER_CLASS = 25
CLASS_GROUPS_PER_GRADE = 3


def main():
    """Create a backup, clear the database and insert random test records."""

    seed = int(datetime.now().timestamp())
    random.seed(seed)

    init_database()
    backup_path = backup_database()

    tasks_by_class = group_tasks_by_class()

    with get_connection() as connection:
        teacher_id = get_test_teacher_id(connection)
        clear_database(connection)

        student_count = 0
        progress_count = 0
        attempt_count = 0

        for school in SCHOOLS:
            for grade in GRADES:
                for class_group, class_name in make_class_names(school, grade):
                    student_names = make_student_names()

                    for student_index, full_name in enumerate(student_names):
                        email = make_student_email(
                            school,
                            grade,
                            class_group,
                            student_count,
                            student_index,
                        )
                        student_id = insert_student(
                            connection,
                            email,
                            school,
                            class_name,
                            grade,
                            class_group,
                            choose_task_class_id(grade),
                            full_name,
                            teacher_id,
                        )
                        student_count += 1

                        class_id = get_student_task_class_id(connection, student_id)
                        progress_added, attempts_added = seed_student_progress(
                            connection,
                            student_id,
                            class_id,
                            tasks_by_class[class_id],
                        )
                        progress_count += progress_added
                        attempt_count += attempts_added

        connection.commit()

    print(f"Seed: {seed}")
    print(f"Backup: {backup_path}")
    print(f"Students: {student_count}")
    print(f"Progress rows: {progress_count}")
    print(f"Attempt rows: {attempt_count}")


def backup_database():
    """Copy the current database before replacing the test data."""

    if not DATABASE_PATH.exists():
        return "no existing database"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DATABASE_PATH.with_name(
        f"{DATABASE_PATH.stem}_backup_before_seed_{timestamp}{DATABASE_PATH.suffix}"
    )
    shutil.copy2(DATABASE_PATH, backup_path)

    return backup_path


def group_tasks_by_class():
    """Group task metadata by class id for quick random sampling."""

    tasks_by_class = defaultdict(list)

    for task in TASKS:
        tasks_by_class[task["class_id"]].append(task)

    return tasks_by_class


def clear_database(connection):
    """Remove student data and reset autoincrement counters."""

    connection.execute("DELETE FROM task_attempts")
    connection.execute("DELETE FROM task_progress")
    connection.execute("DELETE FROM students")
    connection.execute(
        """
        DELETE FROM sqlite_sequence
        WHERE name IN ('students', 'task_attempts', 'task_progress')
        """
    )


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


def make_class_names(school, grade):
    """Return test class names in the naming style of the selected school."""

    if school == LETOVO:
        return [
            (str(number), f"{grade}-{number}")
            for number in range(1, CLASS_GROUPS_PER_GRADE + 1)
        ]

    return [
        (letter, f"{grade}{letter}")
        for letter in FIRST_L2SH_LETTERS[:CLASS_GROUPS_PER_GRADE]
    ]


def make_student_names():
    """Build 25 random full names without duplicates inside one class."""

    numbers = random.sample(range(1, 900), STUDENTS_PER_CLASS)

    return [
        f"{FAMILY_PREFIX}{number:03d} {NAME_PREFIX}{number:03d}"
        for number in sorted(numbers)
    ]


def choose_task_class_id(grade):
    """Pick a task base for generated students."""

    return f"{grade}class"


def make_student_email(school, grade, class_group, student_count, student_index):
    """Return a stable email for generated students and grade test accounts."""

    if school == LETOVO and class_group == "1" and student_index == 0:
        return f"{grade}@test.ru"

    return f"student{student_count + 1:03d}@test.local"


def insert_student(
    connection,
    email,
    school,
    class_name,
    grade,
    class_group,
    task_class_id,
    full_name,
    teacher_id,
):
    """Insert one student and return its id."""

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
            full_name
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            email,
            teacher_id,
            school,
            class_name,
            grade,
            class_group,
            task_class_id,
            full_name,
        ),
    )

    return cursor.lastrowid


def get_student_task_class_id(connection, student_id):
    """Return the task base assigned to a generated student."""

    row = connection.execute(
        """
        SELECT task_class_id
        FROM students
        WHERE id = ?
        """,
        (student_id,),
    ).fetchone()

    return row["task_class_id"]


def seed_student_progress(connection, student_id, class_id, tasks):
    """Insert random attempts and progress for one student."""

    if not tasks:
        return 0, 0

    selected_tasks = random.sample(
        tasks,
        k=random.randint(12, min(45, len(tasks))),
    )
    progress_count = 0
    attempt_count = 0

    for task in selected_tasks:
        attempts = random.randint(1, 4)
        is_passed = 1 if random.random() < pass_probability(attempts) else 0
        updated_at = random_timestamp()

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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                student_id,
                class_id,
                task["chapter"],
                task["topic"],
                task["number"],
                attempts,
                is_passed,
                updated_at,
            ),
        )
        progress_count += 1

        for attempt_index in range(1, attempts + 1):
            attempt_passed = 1 if is_passed and attempt_index == attempts else 0
            connection.execute(
                """
                INSERT INTO task_attempts (
                    student_id,
                    class_id,
                    chapter,
                    topic,
                    number,
                    solution_text,
                    ai_response,
                    is_passed,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    student_id,
                    class_id,
                    task["chapter"],
                    task["topic"],
                    task["number"],
                    f"Test solution, attempt {attempt_index}",
                    '{"status": "test", "comment": "Generated test data"}',
                    attempt_passed,
                    updated_at,
                ),
            )
            attempt_count += 1

    return progress_count, attempt_count


def pass_probability(attempts):
    """Make later attempts more likely to have a passed result."""

    return min(0.25 + attempts * 0.15, 0.8)


def random_timestamp():
    """Return a recent timestamp in SQLite's default text format."""

    moment = datetime.now() - timedelta(
        days=random.randint(0, 45),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )

    return moment.strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    main()
