from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.schemas.booking import BookingRequest


class BookingSlotUnavailableError(ValueError):
    """Raised when an interview time cannot be booked."""


class BookingService:
    """Handle interview booking availability and persistence."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def is_slot_available(self, interview_at: datetime) -> bool:
        """Check whether an exact interview start time is available."""

        if interview_at.tzinfo is None or interview_at.utcoffset() is None:
            raise ValueError(
                "Interview datetime must include a timezone"
            )

        existing_booking = self.db.scalar(
            select(Booking.id)
            .where(
                Booking.interview_at == interview_at,
                Booking.status != "cancelled",
            )
            .limit(1)
        )

        return existing_booking is None

    def create_booking(self, request: BookingRequest) -> Booking:
        """Create a confirmed booking after candidate confirmation."""

        if not self.is_slot_available(request.interview_at):
            raise BookingSlotUnavailableError(
                "The requested interview slot is unavailable"
            )

        booking = Booking(
            id=str(uuid4()),
            candidate_name=request.candidate_name,
            email=str(request.email),
            interview_at=request.interview_at,
            status="confirmed",
        )

        try:
            self.db.add(booking)
            self.db.commit()
            self.db.refresh(booking)

        except IntegrityError as exc:
            self.db.rollback()
            raise BookingSlotUnavailableError(
                "The requested interview slot is no longer available"
            ) from exc

        return booking
