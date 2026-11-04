from datetime import datetime, timedelta, timezone

import pytest

from app.models.booking import Booking
from app.schemas.booking import BookingRequest
from app.services.booking_service import BookingService


def create_request(interview_at=None):
    if interview_at is None:
        interview_at = datetime.now(timezone.utc) + timedelta(days=5)

    return BookingRequest(
        candidate_name="Test Candidate",
        email="test@example.com",
        interview_at=interview_at,
    )


def test_creates_confirmed_booking(db_session):
    service = BookingService(db_session)
    request = create_request()

    result = service.create_booking(request)

    assert result.id is not None
    assert result.candidate_name == "Test Candidate"
    assert result.email == "test@example.com"
    assert result.status == "confirmed"


def test_created_booking_is_persisted(db_session):
    service = BookingService(db_session)
    request = create_request()

    result = service.create_booking(request)

    stored_booking = db_session.get(Booking, result.id)

    assert stored_booking is not None
    assert stored_booking.email == "test@example.com"


def test_rejects_unavailable_slot(db_session):
    service = BookingService(db_session)
    request = create_request()

    service.create_booking(request)

    with pytest.raises(
        ValueError,
        match="slot is unavailable",
    ):
        service.create_booking(request)


def test_generates_unique_booking_ids(db_session):
    service = BookingService(db_session)

    first = service.create_booking(create_request())

    second = service.create_booking(
        create_request(
            datetime.now(timezone.utc) + timedelta(days=6)
        )
    )

    assert first.id != second.id


def test_created_booking_has_correct_status(db_session):
    service = BookingService(db_session)

    result = service.create_booking(create_request())

    assert result.status == "confirmed"
