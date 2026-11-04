from datetime import datetime, timezone
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


class BookingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    interview_at: datetime

    @field_validator("candidate_name")
    @classmethod
    def validate_candidate_name(cls, value: str) -> str:
        value = value.strip()

        if len(value) < 2:
            raise ValueError("Candidate name must contain at least 2 characters")

        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("interview_at")
    @classmethod
    def validate_interview_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Interview datetime must include a timezone")

        if value <= datetime.now(timezone.utc):
            raise ValueError("Interview datetime must be in the future")

        return value


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    candidate_name: str
    email: EmailStr
    interview_at: datetime
    status: str
    created_at: datetime
