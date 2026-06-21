"""Helpers for school records."""

from app.database import database_connection


def row_to_dict(row):
    """Convert sqlite3.Row to a regular dict."""

    if row is None:
        return None

    return dict(row)


def list_active_schools():
    """Return active schools available for teacher class creation."""

    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, name, is_active, created_at
            FROM schools
            WHERE is_active = 1
            ORDER BY name
            """
        ).fetchall()

        return [row_to_dict(row) for row in rows]


def list_admin_schools():
    """Return all schools with class/student counters for admin views."""

    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                schools.id,
                schools.name,
                schools.is_active,
                schools.created_at,
                COALESCE(class_summary.active_classes, 0) AS active_classes,
                COALESCE(class_summary.archived_classes, 0) AS archived_classes,
                COALESCE(student_summary.active_students, 0) AS active_students
            FROM schools
            LEFT JOIN (
                SELECT
                    school,
                    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active_classes,
                    SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) AS archived_classes
                FROM classes
                GROUP BY school
            ) AS class_summary
                ON class_summary.school = schools.name
            LEFT JOIN (
                SELECT school, COUNT(*) AS active_students
                FROM students
                WHERE is_active = 1
                GROUP BY school
            ) AS student_summary
                ON student_summary.school = schools.name
            ORDER BY schools.name
            """
        ).fetchall()

        return [row_to_dict(row) for row in rows]


def active_school_exists(name):
    """Return whether a school name is available for class creation."""

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT id
            FROM schools
            WHERE name = ?
              AND is_active = 1
            LIMIT 1
            """,
            ((name or "").strip(),),
        ).fetchone()

        return row is not None


def upsert_school(name, school_id=None):
    """Create a school or rename an existing one.

    Classes and students keep the school name as a denormalized display field,
    so renaming a school must update all three places in one transaction.
    """

    name = (name or "").strip()

    if not name:
        return None

    with database_connection() as connection:
        duplicate = connection.execute(
            """
            SELECT id
            FROM schools
            WHERE name = ?
              AND (? IS NULL OR id != ?)
            LIMIT 1
            """,
            (name, school_id, school_id),
        ).fetchone()

        if duplicate is not None:
            return {
                "blocked": True,
                "detail": "duplicate",
            }

        if school_id is None:
            cursor = connection.execute(
                """
                INSERT INTO schools (name, is_active)
                VALUES (?, 1)
                """,
                (name,),
            )
            saved_id = cursor.lastrowid
            action = "created"
        else:
            row = connection.execute(
                """
                SELECT id, name
                FROM schools
                WHERE id = ?
                LIMIT 1
                """,
                (school_id,),
            ).fetchone()

            if row is None:
                return None

            old_name = row["name"]
            saved_id = row["id"]

            connection.execute(
                """
                UPDATE schools
                SET name = ?,
                    is_active = 1
                WHERE id = ?
                """,
                (name, saved_id),
            )
            connection.execute(
                """
                UPDATE classes
                SET school = ?
                WHERE school = ?
                """,
                (name, old_name),
            )
            connection.execute(
                """
                UPDATE students
                SET school = ?
                WHERE school = ?
                """,
                (name, old_name),
            )
            action = "updated"

        row = connection.execute(
            """
            SELECT id, name, is_active, created_at
            FROM schools
            WHERE id = ?
            """,
            (saved_id,),
        ).fetchone()

        result = row_to_dict(row)
        result["action"] = action
        return result


def deactivate_school(school_id):
    """Archive a school if it has no active classes."""

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT schools.id, COUNT(classes.id) AS active_classes
            FROM schools
            LEFT JOIN classes
                ON classes.school = schools.name
                AND classes.is_active = 1
            WHERE schools.id = ?
              AND schools.is_active = 1
            GROUP BY schools.id
            LIMIT 1
            """,
            (school_id,),
        ).fetchone()

        if row is None:
            return None

        if row["active_classes"] > 0:
            return {
                "id": school_id,
                "blocked": True,
                "active_classes": row["active_classes"],
            }

        connection.execute(
            """
            UPDATE schools
            SET is_active = 0
            WHERE id = ?
            """,
            (school_id,),
        )

        return {
            "id": school_id,
            "is_active": 0,
        }


def restore_school(school_id):
    """Reactivate an archived school."""

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT id
            FROM schools
            WHERE id = ?
              AND is_active = 0
            LIMIT 1
            """,
            (school_id,),
        ).fetchone()

        if row is None:
            return None

        connection.execute(
            """
            UPDATE schools
            SET is_active = 1
            WHERE id = ?
            """,
            (school_id,),
        )

        return {
            "id": school_id,
            "is_active": 1,
        }
