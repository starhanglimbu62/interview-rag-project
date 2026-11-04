from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.booking import BookingResponse
from app.schemas.booking_extraction import BookingExtraction


class BookingConversationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=4000)
    conversation_id: UUID | None = None
    confirm_booking: bool = False

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Message cannot be empty")

        return value


class BookingConversationResponse(BaseModel):
    conversation_id: UUID
    message: str

    status: Literal[
        "collecting_details",
        "awaiting_confirmation",
        "slot_unavailable",
        "confirmed",
    ]

    missing_fields: list[str] = Field(default_factory=list)
    booking_details: BookingExtraction | None = None
    booking: BookingResponse | None = None
