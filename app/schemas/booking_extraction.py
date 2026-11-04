from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


class BookingExtraction(BaseModel):
    """Represent booking details extracted from a conversation."""

    model_config = ConfigDict(extra="forbid")

    candidate_name: str | None = Field(
        default=None,
        max_length=150,
    )

    email: EmailStr | None = None

    interview_at: datetime | None = None

    @field_validator("candidate_name")
    @classmethod
    def normalize_candidate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value or None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        if value is None:
            return None

        return str(value).strip().lower()

    @field_validator("interview_at")
    @classmethod
    def validate_interview_timezone(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError(
                "Interview datetime must include a timezone"
            )

        return value
