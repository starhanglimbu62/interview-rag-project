import json
from uuid import UUID

import redis

from app.config import settings


class RedisChatMemory:
    """Store and retrieve bounded conversation history in Redis."""

    ALLOWED_ROLES = {"user", "assistant"}

    def __init__(
        self,
        client: redis.Redis | None = None,
        ttl_seconds: int = settings.redis_ttl_seconds,
        max_messages: int = settings.chat_history_limit,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("TTL must be greater than zero")

        if max_messages <= 0:
            raise ValueError("Maximum messages must be greater than zero")

        self.client = client or redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
        self.ttl_seconds = ttl_seconds
        self.max_messages = max_messages

    @staticmethod
    def _get_key(conversation_id: UUID) -> str:
        return f"chat:conversation:{conversation_id}:messages"

    def get_history(self, conversation_id: UUID) -> list[dict[str, str]]:
        """Return validated conversation messages in chronological order."""
        key = self._get_key(conversation_id)
        stored_messages = self.client.lrange(key, 0, -1)

        try:
            messages = [json.loads(message) for message in stored_messages]
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Stored conversation history is corrupted"
            ) from exc

        for message in messages:
            if (
                not isinstance(message, dict)
                or message.get("role") not in self.ALLOWED_ROLES
                or not isinstance(message.get("content"), str)
                or not message["content"].strip()
            ):
                raise RuntimeError(
                    "Stored conversation history contains invalid messages"
                )

        return messages

    def add_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
    ) -> None:
        """Append a message and enforce history size and expiration."""
        if role not in self.ALLOWED_ROLES:
            raise ValueError("Role must be user or assistant")

        if not content or not content.strip():
            raise ValueError("Message content cannot be empty")

        key = self._get_key(conversation_id)
        message = json.dumps({
            "role": role,
            "content": content.strip(),
        })

        pipeline = self.client.pipeline(transaction=True)
        pipeline.rpush(key, message)
        pipeline.ltrim(key, -self.max_messages, -1)
        pipeline.expire(key, self.ttl_seconds)
        pipeline.execute()
