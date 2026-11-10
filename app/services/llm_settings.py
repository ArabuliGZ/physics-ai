"""Persistent application-wide LLM selection."""

import sqlite3

from dotenv import load_dotenv

load_dotenv()

from app.database import database_connection
from config import LETOVO_LLM_MODEL
from config import MODEL_PROVIDER
from config import QWEN_CLOUD_MODEL
from config import TIMEWEB_LLM_MODEL


LLM_PROVIDER_SETTING_KEY = "active_llm_provider"
LLM_PROVIDER_OPTIONS = (
    {
        "provider": "letovo",
        "label": "Letovo",
        "model": LETOVO_LLM_MODEL,
    },
    {
        "provider": "qwencloud",
        "label": "QwenCloud",
        "model": QWEN_CLOUD_MODEL,
    },
    {
        "provider": "timeweb",
        "label": "Timeweb GPT",
        "model": TIMEWEB_LLM_MODEL,
    },
)
VALID_LLM_PROVIDERS = {
    option["provider"]
    for option in LLM_PROVIDER_OPTIONS
}


def normalize_llm_provider(provider):
    """Return a supported provider id or the configured fallback."""

    normalized = str(provider or "").strip().lower()

    if normalized == "qwen":
        normalized = "qwencloud"

    if normalized in VALID_LLM_PROVIDERS:
        return normalized

    fallback = str(MODEL_PROVIDER or "").strip().lower()

    if fallback == "qwen":
        fallback = "qwencloud"

    return fallback if fallback in VALID_LLM_PROVIDERS else "qwencloud"


def get_stored_llm_provider():
    """Return the database override, or None before an admin selects one."""

    try:
        with database_connection() as connection:
            row = connection.execute(
                """
                SELECT value
                FROM app_settings
                WHERE key = ?
                """,
                (LLM_PROVIDER_SETTING_KEY,),
            ).fetchone()
    except sqlite3.OperationalError:
        return None

    if row is None:
        return None

    provider = str(row["value"] or "").strip().lower()

    return provider if provider in VALID_LLM_PROVIDERS else None


def get_active_llm_provider():
    """Return the provider used for the next LLM request."""

    return get_stored_llm_provider() or normalize_llm_provider(MODEL_PROVIDER)


def get_llm_settings():
    """Return public model choices without exposing credentials."""

    stored_provider = get_stored_llm_provider()

    return {
        "active_provider": (
            stored_provider
            or normalize_llm_provider(MODEL_PROVIDER)
        ),
        "source": "database" if stored_provider else "environment",
        "options": list(LLM_PROVIDER_OPTIONS),
    }


def set_active_llm_provider(provider, updated_by):
    """Persist one validated provider for all subsequent checks."""

    normalized = str(provider or "").strip().lower()

    if normalized not in VALID_LLM_PROVIDERS:
        raise ValueError("unsupported_llm_provider")

    with database_connection() as connection:
        connection.execute(
            """
            INSERT INTO app_settings (key, value, updated_by, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_by = excluded.updated_by,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                LLM_PROVIDER_SETTING_KEY,
                normalized,
                updated_by,
            ),
        )

    return get_llm_settings()
