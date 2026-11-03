from typing import Any

import httpx

from app.config import settings


class LLMService:
    """Generate responses using a locally hosted Ollama model."""

    def __init__(self, client: Any = None) -> None:
        self.model = settings.ollama_model

        if client is not None:
            self.client = client
        else:
            self.client = httpx.Client(
                base_url=settings.ollama_base_url,
                timeout=settings.llm_timeout_seconds
            )

    def generate(
        self,
        messages: list[dict[str, str]]
    ) -> str:
        """Send chat messages to Ollama and return the generated response."""

        if not messages:
            raise ValueError("Messages cannot be empty")

        allowed_roles = {"system", "user", "assistant"}

        for message in messages:
            if message.get("role") not in allowed_roles:
                raise ValueError("Invalid message role")

            content = message.get("content")

            if not isinstance(content, str) or not content.strip():
                raise ValueError("Message content cannot be empty")

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0.2
            }
        }

        response = self.client.post(
            "/api/chat",
            json=payload
        )

        response.raise_for_status()

        data = response.json()
        content = data.get("message", {}).get("content")

        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("LLM returned an empty response")

        return content.strip()