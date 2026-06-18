"""SQLite database setup for students and task progress."""

from pathlib import Path
from contextlib import contextmanager
import sqlite3


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
                school TEXT NOT NULL,
                class_name TEXT NOT NULL,
                full_name TEXT NOT NULL,
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
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
                UNIQUE (student_id, class_id, chapter, topic, number)
            );
            """
        )
