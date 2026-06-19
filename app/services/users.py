"""Helpers for role-based users."""

from app.database import database_connection


def row_to_dict(row):
    """Convert sqlite3.Row to a regular dict."""

    if row is None:
        return None

    return dict(row)


def normalize_email(email):
    """Normalize email for stable lookup."""

    return (email or "").strip().lower()


def find_user_by_email(email):
    """Return an active user by email."""

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT id, email, role, full_name, is_active, created_at
            FROM users
            WHERE lower(email) = ?
              AND is_active = 1
            ORDER BY id
            LIMIT 1
            """,
            (normalize_email(email),),
        ).fetchone()

        return row_to_dict(row)
