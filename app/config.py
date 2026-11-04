import os
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()


def _validated_http_url(name: str, default: str) -> str:
    value = os.getenv(name, default).strip().rstrip("/")
    parsed = urlparse(value)

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(
            f"{name} must be an absolute HTTP or HTTPS URL"
        )

    return value


class Settings:
    """Application settings loaded from environment variables."""

    app_env: str = os.getenv("APP_ENV", "development").strip().lower()
    api_key: str | None = os.getenv("API_KEY") or None
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama")

    ollama_base_url: str = os.getenv(
        "OLLAMA_BASE_URL",
        "http://localhost:11434"
    ).rstrip("/")
    qdrant_url: str = _validated_http_url(
        "QDRANT_URL",
        "http://localhost:6333"
    )

    ollama_model: str = os.getenv(
        "OLLAMA_MODEL",
        "qwen3:1.7b"
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_ttl_seconds: int = int(os.getenv("REDIS_TTL_SECONDS", "86400"))
    chat_history_limit: int = int(os.getenv("CHAT_HISTORY_LIMIT", "10"))
    health_timeout_seconds: float = float(
        os.getenv("HEALTH_TIMEOUT_SECONDS", "5")
    )

    llm_timeout_seconds: float = float(
        os.getenv("LLM_TIMEOUT_SECONDS", "120")
    )


settings = Settings()
