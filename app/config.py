import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama")

    ollama_base_url: str = os.getenv(
        "OLLAMA_BASE_URL",
        "http://localhost:11434"
    ).rstrip("/")

    ollama_model: str = os.getenv(
        "OLLAMA_MODEL",
        "qwen3:1.7b"
    )

    llm_timeout_seconds: float = float(
        os.getenv("LLM_TIMEOUT_SECONDS", "120")
    )


settings = Settings()