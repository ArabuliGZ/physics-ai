import os


# Non-secret application configuration.
# Secrets live in .env and are read only where they are needed.


# LLM provider selection.
# Available values: "letovo", "qwencloud", "timeweb".
MODEL_PROVIDER = os.getenv(
    "MODEL_PROVIDER",
    "qwencloud",
).strip().lower()


# Letovo Open WebUI / OpenAI-compatible endpoint.
LETOVO_LLM_API_URL = "https://llm.letovo.site/openai/chat/completions"
LETOVO_LLM_MODEL = "deepseek-v4-flash"
LETOVO_REASONING_EFFORT = "low"
LETOVO_MAX_COMPLETION_TOKENS = 2500


# QwenCloud / DashScope OpenAI-compatible endpoint.
# Change MODEL_PROVIDER to "qwencloud" to use it.
QWEN_CLOUD_LLM_API_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
QWEN_CLOUD_MODEL = "qwen3.7-plus"
QWEN_CLOUD_ENABLE_THINKING = False


# Timeweb AI Gateway / OpenAI-compatible endpoint.
TIMEWEB_LLM_API_URL = "https://api.timeweb.ai/v1/chat/completions"
TIMEWEB_LLM_MODEL = "openai/gpt-6-luna"
TIMEWEB_MAX_COMPLETION_TOKENS = 5000


# Shared LLM generation settings.
MAX_TOKENS = 700
TEMPERATURE = 0.2
# Three sequential provider attempts must stay below the proxy timeout.
LLM_REQUEST_TIMEOUT = 55


# Uploaded solution images are compressed in the browser, but the backend keeps
# the same hard safety limit for direct API requests.
MAX_SOLUTION_IMAGE_BYTES = 10 * 1024 * 1024
HEIC_SOLUTION_ATTACHMENT_MIME_TYPES = {
    "image/heic",
    "image/heif",
}
ALLOWED_SOLUTION_ATTACHMENT_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    *HEIC_SOLUTION_ATTACHMENT_MIME_TYPES,
}


DEBUG = True
