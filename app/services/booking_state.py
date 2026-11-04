import hashlib
from uuid import UUID

import redis
from pydantic import ValidationError

from app.config import settings
from app.schemas.booking_extraction import BookingExtraction


class RedisBookingState:
    """Store temporary booking details and confirmation readiness."""

    def __init__(
        self,
        client: redis.Redis | None = None,
        ttl_seconds: int = settings.redis_ttl_seconds,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("TTL must be greater than zero")

        self.client = client or redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def _get_key(conversation_id: UUID) -> str:
        return f"chat:conversation:{conversation_id}:booking"

    @staticmethod
    def _get_confirmation_key(conversation_id: UUID) -> str:
        return f"chat:conversation:{conversation_id}:booking:confirmation"

    @staticmethod
    def _get_fingerprint(state: BookingExtraction) -> str:
        """Generate a fingerprint for the exact booking details."""

        serialized_state = state.model_dump_json()
        return hashlib.sha256(
            serialized_state.encode("utf-8")
        ).hexdigest()

    def get_state(
        self,
        conversation_id: UUID,
    ) -> BookingExtraction | None:
        """Retrieve and validate temporary booking details."""

        stored_state = self.client.get(
            self._get_key(conversation_id)
        )

        if stored_state is None:
            return None

        if isinstance(stored_state, bytes):
            stored_state = stored_state.decode("utf-8")

        try:
            return BookingExtraction.model_validate_json(stored_state)
        except (ValidationError, ValueError) as exc:
            raise RuntimeError(
                "Stored booking state is corrupted or invalid"
            ) from exc

    def save_state(
        self,
        conversation_id: UUID,
        state: BookingExtraction,
    ) -> None:
        """Save details and invalidate previous confirmation readiness."""

        if not isinstance(state, BookingExtraction):
            raise TypeError("State must be a BookingExtraction instance")

        self.client.set(
            self._get_key(conversation_id),
            state.model_dump_json(),
            ex=self.ttl_seconds,
        )

        self.client.delete(
            self._get_confirmation_key(conversation_id)
        )

    def mark_awaiting_confirmation(
        self,
        conversation_id: UUID,
    ) -> None:
        """Bind confirmation readiness to the current booking details."""

        state = self.get_state(conversation_id)

        if state is None:
            raise ValueError("Cannot confirm missing booking details")

        fingerprint = self._get_fingerprint(state)

        self.client.set(
            self._get_confirmation_key(conversation_id),
            fingerprint,
            ex=self.ttl_seconds,
        )

    def is_awaiting_confirmation(
        self,
        conversation_id: UUID,
    ) -> bool:
        """Verify confirmation readiness against current booking details."""

        state = self.get_state(conversation_id)

        if state is None:
            return False

        stored_fingerprint = self.client.get(
            self._get_confirmation_key(conversation_id)
        )

        if isinstance(stored_fingerprint, bytes):
            stored_fingerprint = stored_fingerprint.decode("utf-8")

        current_fingerprint = self._get_fingerprint(state)

        return stored_fingerprint == current_fingerprint

    def clear_state(self, conversation_id: UUID) -> None:
        """Delete booking details and confirmation readiness."""

        self.client.delete(
            self._get_key(conversation_id),
            self._get_confirmation_key(conversation_id),
        )
