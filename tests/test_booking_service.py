from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.models.booking import Booking
from app.services.booking_service import BookingService


def future_interview_time():
    return datetime.now(timezone.utc) + timedelta(days=5)


def create_booking(db_session, interview_at, status="pending"):
    booking = Booking(
        id=str(uuid4()),
        candidate_name="Test Candidate",
        email="test@example.com",
        interview_at=interview_at,
        status=status,
    )

    db_session.add(booking)
    db_session.commit()

    return booking


def test_available_slot_returns_true(db_session):
    service = BookingService(db_session)

    result = service.is_slot_available(future_interview_time())

    assert result is True


@pytest.mark.parametrize("status", ["pending", "confirmed"])
def test_active_booking_makes_slot_unavailable(db_session, status):
    interview_at = future_interview_time()

    create_booking(db_session, interview_at, status)

    service = BookingService(db_session)

    assert service.is_slot_available(interview_at) is False


def test_cancelled_booking_releases_slot(db_session):
    interview_at = future_interview_time()

    create_booking(db_session, interview_at, "cancelled")

    service = BookingService(db_session)

    assert service.is_slot_available(interview_at) is True


def test_different_interview_time_is_available(db_session):
    interview_at = future_interview_time()

    create_booking(db_session, interview_at)

    different_time = interview_at + timedelta(hours=1)

    service = BookingService(db_session)

    assert service.is_slot_available(different_time) is True


def test_rejects_naive_interview_datetime(db_session):
    service = BookingService(db_session)

    with pytest.raises(
        ValueError,
        match="must include a timezone",
    ):
        service.is_slot_available(datetime.now())
