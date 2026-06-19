"""SQLite database setup for students and task progress."""

from pathlib import Path
from contextlib import contextmanager
import sqlite3
import re


DATABASE_PATH = Path("data") / "physics_ai.db"


def get_connection():
    """Open a SQLite connection with project defaults enabled."""

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


@contextmanager
def database_connection():
    """Open a connection and always close it after the operation."""

    connection = get_connection()

    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_database():
    """Create database tables if they do not exist yet."""

    with database_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER,
                email TEXT,
                school TEXT NOT NULL,
                class_name TEXT NOT NULL,
                grade INTEGER,
                class_group TEXT,
                task_class_id TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                full_name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES users (id)
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL CHECK (role IN ('admin', 'teacher')),
                full_name TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS task_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                class_id TEXT NOT NULL,
                chapter TEXT NOT NULL,
                topic TEXT NOT NULL,
                number TEXT NOT NULL,
                solution_text TEXT NOT NULL,
                ai_response TEXT,
                is_passed INTEGER NOT NULL DEFAULT 0 CHECK (is_passed IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS task_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                class_id TEXT NOT NULL,
                chapter TEXT NOT NULL,
                topic TEXT NOT NULL,
                number TEXT NOT NULL,
                attempts_count INTEGER NOT NULL DEFAULT 0,
                is_passed INTEGER NOT NULL DEFAULT 0 CHECK (is_passed IN (0, 1)),
                teacher_override INTEGER CHECK (teacher_override IN (0, 1)),
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
                UNIQUE (student_id, class_id, chapter, topic, number)
            );
            """
        )

        ensure_user_rows(connection)
        ensure_student_class_columns(connection)
        ensure_task_progress_columns(connection)
        backfill_student_teacher(connection)
        backfill_student_class_parts(connection)
        backfill_student_task_class(connection)


def ensure_user_rows(connection):
    """Create stable local test users for role-based login."""

    users = (
        ("teacher@test.ru", "teacher", "Тестовый учитель"),
        ("admin@test.ru", "admin", "Администратор"),
    )

    for email, role, full_name in users:
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


def ensure_student_class_columns(connection):
    """Add structured class columns to older local databases."""

    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(students)").fetchall()
    }

    if "grade" not in columns:
        connection.execute("ALTER TABLE students ADD COLUMN grade INTEGER")

    if "teacher_id" not in columns:
        connection.execute("ALTER TABLE students ADD COLUMN teacher_id INTEGER")

    if "class_group" not in columns:
        connection.execute("ALTER TABLE students ADD COLUMN class_group TEXT")

    if "task_class_id" not in columns:
        connection.execute("ALTER TABLE students ADD COLUMN task_class_id TEXT")

    if "email" not in columns:
        connection.execute("ALTER TABLE students ADD COLUMN email TEXT")

    if "is_active" not in columns:
        connection.execute(
            "ALTER TABLE students ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1"
        )


def ensure_task_progress_columns(connection):
    """Add progress metadata columns to older local databases."""

    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(task_progress)").fetchall()
    }

    if "teacher_override" not in columns:
        connection.execute(
            "ALTER TABLE task_progress ADD COLUMN teacher_override INTEGER CHECK (teacher_override IN (0, 1))"
        )


def backfill_student_teacher(connection):
    """Attach older students to the local test teacher."""

    teacher = connection.execute(
        """
        SELECT id
        FROM users
        WHERE email = 'teacher@test.ru'
        """
    ).fetchone()

    if teacher is None:
        return

    connection.execute(
        """
        UPDATE students
        SET teacher_id = ?
        WHERE teacher_id IS NULL
        """,
        (teacher["id"],),
    )


def backfill_student_class_parts(connection):
    """Fill grade and class_group for students created before the migration."""

    rows = connection.execute(
        """
        SELECT id, class_name
        FROM students
        WHERE grade IS NULL
           OR class_group IS NULL
        """
    ).fetchall()

    for row in rows:
        grade, class_group = parse_class_name(row["class_name"])

        if grade is None:
            continue

        connection.execute(
            """
            UPDATE students
            SET grade = ?,
                class_group = ?
            WHERE id = ?
            """,
            (grade, class_group, row["id"]),
        )


def backfill_student_task_class(connection):
    """Fill default task base ids for students created before this field."""

    rows = connection.execute(
        """
        SELECT id, grade
        FROM students
        WHERE task_class_id IS NULL
           OR task_class_id = ''
        """
    ).fetchall()

    for row in rows:
        if row["grade"] is None:
            continue

        connection.execute(
            """
            UPDATE students
            SET task_class_id = ?
            WHERE id = ?
            """,
            (f"{row['grade']}class", row["id"]),
        )


def parse_class_name(class_name):
    """Split display class names like 7-1 or 7A into grade and class group."""

    match = re.match(r"^\s*(\d+)\s*[-\s]?\s*(.*)\s*$", class_name or "")

    if match is None:
        return None, None

    grade = int(match.group(1))
    class_group = match.group(2).strip() or None

    return grade, class_group
