# Non-secret application configuration.
# Secrets live in .env and are read only where they are needed.


# LLM provider selection.
# Available values: "letovo", "openrouter".
MODEL_PROVIDER = "letovo"


# Letovo Open WebUI / OpenAI-compatible endpoint.
LETOVO_LLM_API_URL = "https://llm.letovo.site/openai/chat/completions"
LETOVO_LLM_MODEL = "gemma-4-26b"


# OpenRouter fallback. Change MODEL_PROVIDER to "openrouter" to use it.
# OPENROUTER_MODEL = "anthropic/claude-sonnet-4"
OPENROUTER_MODEL = "qwen/qwen3-vl-235b-a22b-thinking"


# Shared LLM generation settings.
MAX_TOKENS = 700
TEMPERATURE = 0.2
LLM_REQUEST_TIMEOUT = 180


# Uploaded solution images are compressed in the browser, but the backend keeps
# the same hard safety limit for direct API requests.
MAX_SOLUTION_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_SOLUTION_ATTACHMENT_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


DEBUG = True
