"""SQLite database setup for students and task progress."""

from pathlib import Path
from contextlib import contextmanager
import sqlite3
import re

from app.security import hash_password


DATABASE_PATH = Path("data") / "physics_ai.db"
DEFAULT_TEST_PASSWORD = "test"


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
                class_id INTEGER,
                teacher_id INTEGER,
                email TEXT,
                password_hash TEXT,
                school TEXT NOT NULL,
                class_name TEXT NOT NULL,
                grade INTEGER,
                class_group TEXT,
                task_class_id TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                full_name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (class_id) REFERENCES classes (id),
                FOREIGN KEY (teacher_id) REFERENCES users (id)
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT,
                role TEXT NOT NULL CHECK (role IN ('admin', 'teacher')),
                full_name TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER,
                school TEXT NOT NULL,
                grade INTEGER NOT NULL,
                class_group TEXT NOT NULL DEFAULT '',
                class_name TEXT NOT NULL,
                task_class_id TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES users (id),
                UNIQUE (teacher_id, school, grade, class_group, task_class_id)
            );

            CREATE TABLE IF NOT EXISTS schools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS student_sessions (
                token TEXT PRIMARY KEY,
                student_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
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

        ensure_password_columns(connection)
        ensure_user_rows(connection)
        backfill_password_hashes(connection)
        ensure_student_class_columns(connection)
        ensure_task_progress_columns(connection)
        backfill_student_teacher(connection)
        backfill_student_class_parts(connection)
        backfill_student_task_class(connection)
        sync_student_classes(connection)
        sync_schools(connection)


def ensure_user_rows(connection):
    """Create stable local test users for role-based login."""

    password_hash = hash_password(DEFAULT_TEST_PASSWORD)
    users = (
        ("teacher@test.ru", "teacher", "Тестовый учитель"),
        ("admin@test.ru", "admin", "Администратор"),
    )

    for email, role, full_name in users:
        connection.execute(
            """
            INSERT INTO users (email, password_hash, role, full_name, is_active)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(email) DO UPDATE SET
                password_hash = COALESCE(users.password_hash, excluded.password_hash),
                role = excluded.role,
                full_name = excluded.full_name,
                is_active = 1
            """,
            (email, password_hash, role, full_name),
        )


def ensure_password_columns(connection):
    """Add password hash columns to existing local databases."""

    user_columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)")}
    student_columns = {row["name"] for row in connection.execute("PRAGMA table_info(students)")}

    if "password_hash" not in user_columns:
        connection.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")

    if "password_hash" not in student_columns:
        connection.execute("ALTER TABLE students ADD COLUMN password_hash TEXT")


def backfill_password_hashes(connection):
    """Give existing demo-era accounts the temporary password 'test'."""

    password_hash = hash_password(DEFAULT_TEST_PASSWORD)

    connection.execute(
        """
        UPDATE users
        SET password_hash = ?
        WHERE password_hash IS NULL
           OR password_hash = ''
        """,
        (password_hash,),
    )
    connection.execute(
        """
        UPDATE students
        SET password_hash = ?
        WHERE password_hash IS NULL
           OR password_hash = ''
        """,
        (password_hash,),
    )


def sync_schools(connection=None):
    """Create active school rows from known data and stable demo defaults."""

    if connection is None:
        with database_connection() as managed_connection:
            sync_schools(managed_connection)
        return

    school_names = {"Тестовая школа"}

    rows = connection.execute(
        """
        SELECT school
        FROM classes
        WHERE school IS NOT NULL
          AND school != ''
        UNION
        SELECT school
        FROM students
        WHERE school IS NOT NULL
          AND school != ''
        """
    ).fetchall()

    for row in rows:
        school_names.add(row["school"])

    for school_name in sorted(school_names):
        connection.execute(
            """
            INSERT INTO schools (name, is_active)
            VALUES (?, 1)
            ON CONFLICT(name) DO UPDATE SET
                is_active = 1
            """,
            (school_name,),
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

    if "class_id" not in columns:
        connection.execute("ALTER TABLE students ADD COLUMN class_id INTEGER")

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


def sync_student_classes(connection=None):
    """Create class rows from student snapshots and attach students to them."""

    if connection is None:
        with database_connection() as managed_connection:
            sync_student_classes(managed_connection)
        return

    rows = connection.execute(
        """
        SELECT id, teacher_id, school, class_name, grade, class_group, task_class_id
        FROM students
        WHERE is_active = 1
          AND teacher_id IS NOT NULL
          AND school IS NOT NULL
          AND school != ''
          AND grade IS NOT NULL
          AND task_class_id IS NOT NULL
          AND task_class_id != ''
        """
    ).fetchall()

    for row in rows:
        class_group = row["class_group"] or ""
        class_id = ensure_class_row(
            connection,
            row["teacher_id"],
            row["school"],
            row["grade"],
            class_group,
            row["class_name"],
            row["task_class_id"],
        )

        if row["id"] is not None:
            connection.execute(
                """
                UPDATE students
                SET class_id = ?
                WHERE id = ?
                  AND (class_id IS NULL OR class_id != ?)
                """,
                (class_id, row["id"], class_id),
            )


def ensure_class_row(
    connection,
    teacher_id,
    school,
    grade,
    class_group,
    class_name,
    task_class_id,
):
    """Return an existing class row id or create it from student data."""

    if teacher_id is None:
        row = connection.execute(
            """
            SELECT id
            FROM classes
            WHERE teacher_id IS NULL
              AND school = ?
              AND grade = ?
              AND class_group = ?
              AND task_class_id = ?
            LIMIT 1
            """,
            (
                school,
                grade,
                class_group,
                task_class_id,
            ),
        ).fetchone()
    else:
        row = connection.execute(
            """
            SELECT id
            FROM classes
            WHERE teacher_id = ?
              AND school = ?
              AND grade = ?
              AND class_group = ?
              AND task_class_id = ?
            LIMIT 1
            """,
            (
                teacher_id,
                school,
                grade,
                class_group,
                task_class_id,
            ),
        ).fetchone()

    if row is not None:
        connection.execute(
            """
            UPDATE classes
            SET class_name = ?,
                is_active = 1
            WHERE id = ?
            """,
            (class_name, row["id"]),
        )
        return row["id"]

    cursor = connection.execute(
        """
        INSERT INTO classes (
            teacher_id,
            school,
            grade,
            class_group,
            class_name,
            task_class_id,
            is_active
        )
        VALUES (?, ?, ?, ?, ?, ?, 1)
        """,
        (
            teacher_id,
            school,
            grade,
            class_group,
            class_name,
            task_class_id,
        ),
    )

    return cursor.lastrowid


def parse_class_name(class_name):
    """Split display class names like 7-1 or 7A into grade and class group."""

    match = re.match(r"^\s*(\d+)\s*[-\s]?\s*(.*)\s*$", class_name or "")

    if match is None:
        return None, None

    grade = int(match.group(1))
    class_group = match.group(2).strip() or None

    return grade, class_group
