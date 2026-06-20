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


def get_active_teacher(teacher_id):
    """Return an active teacher by id."""

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT id, email, role, full_name, is_active, created_at
            FROM users
            WHERE id = ?
              AND role = 'teacher'
              AND is_active = 1
            LIMIT 1
            """,
            (teacher_id,),
        ).fetchone()

        return row_to_dict(row)


def list_admin_teachers():
    """Return teachers with class counters for admin views."""

    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                users.id,
                users.email,
                users.role,
                users.full_name,
                users.is_active,
                users.created_at,
                COALESCE(class_summary.active_classes, 0) AS active_classes,
                COALESCE(class_summary.archived_classes, 0) AS archived_classes
            FROM users
            LEFT JOIN (
                SELECT
                    teacher_id,
                    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active_classes,
                    SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) AS archived_classes
                FROM classes
                WHERE teacher_id IS NOT NULL
                GROUP BY teacher_id
            ) AS class_summary
                ON class_summary.teacher_id = users.id
            WHERE users.role = 'teacher'
            ORDER BY users.is_active DESC, users.full_name, users.email
            """
        ).fetchall()

        return [row_to_dict(row) for row in rows]


def upsert_teacher(email, full_name):
    """Create or reactivate a teacher by email."""

    normalized_email = normalize_email(email)
    full_name = (full_name or "").strip()

    with database_connection() as connection:
        existing = connection.execute(
            """
            SELECT id
            FROM users
            WHERE lower(email) = ?
            LIMIT 1
            """,
            (normalized_email,),
        ).fetchone()

        if existing is None:
            cursor = connection.execute(
                """
                INSERT INTO users (email, role, full_name, is_active)
                VALUES (?, 'teacher', ?, 1)
                """,
                (normalized_email, full_name),
            )
            teacher_id = cursor.lastrowid
            action = "created"
        else:
            teacher_id = existing["id"]
            connection.execute(
                """
                UPDATE users
                SET role = 'teacher',
                    full_name = ?,
                    is_active = 1
                WHERE id = ?
                """,
                (full_name, teacher_id),
            )
            action = "updated"

        row = connection.execute(
            """
            SELECT id, email, role, full_name, is_active, created_at
            FROM users
            WHERE id = ?
            """,
            (teacher_id,),
        ).fetchone()

        result = row_to_dict(row)
        result["action"] = action
        return result


def deactivate_teacher(teacher_id):
    """Archive a teacher if no active classes are assigned to them."""

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT users.id, COUNT(classes.id) AS active_classes
            FROM users
            LEFT JOIN classes
                ON classes.teacher_id = users.id
                AND classes.is_active = 1
            WHERE users.id = ?
              AND users.role = 'teacher'
              AND users.is_active = 1
            GROUP BY users.id
            LIMIT 1
            """,
            (teacher_id,),
        ).fetchone()

        if row is None:
            return None

        if row["active_classes"] > 0:
            return {
                "id": teacher_id,
                "blocked": True,
                "active_classes": row["active_classes"],
            }

        connection.execute(
            """
            UPDATE users
            SET is_active = 0
            WHERE id = ?
            """,
            (teacher_id,),
        )

        return {
            "id": teacher_id,
            "is_active": 0,
        }


def restore_teacher(teacher_id):
    """Reactivate an archived teacher."""

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT id
            FROM users
            WHERE id = ?
              AND role = 'teacher'
              AND is_active = 0
            LIMIT 1
            """,
            (teacher_id,),
        ).fetchone()

        if row is None:
            return None

        connection.execute(
            """
            UPDATE users
            SET is_active = 1
            WHERE id = ?
            """,
            (teacher_id,),
        )

        return {
            "id": teacher_id,
            "is_active": 1,
        }
