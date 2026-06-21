import os


def env_int(name, default):
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return default

    return int(value)


def env_float(name, default):
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return default

    return float(value)


def env_bool(name, default):
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


# LLM settings. Values can be overridden in .env on the server.
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "openrouter")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4")
#OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "qwen/qwen3-vl-235b-a22b-thinking")
MAX_TOKENS = env_int("MAX_TOKENS", 700)
TEMPERATURE = env_float("TEMPERATURE", 0.2)


DEBUG = env_bool("DEBUG", True)
