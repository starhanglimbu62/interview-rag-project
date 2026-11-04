from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.booking import Booking


def test_booking_can_be_created_and_retrieved(db_session):
    booking_id = str(uuid4())
    interview_at = datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc)

    booking = Booking(
        id=booking_id,
        candidate_name="Test Candidate",
        email="candidate@example.com",
        interview_at=interview_at,
    )

    db_session.add(booking)
    db_session.commit()

    saved_booking = db_session.get(Booking, booking_id)

    assert saved_booking is not None
    assert saved_booking.candidate_name == "Test Candidate"
    assert saved_booking.email == "candidate@example.com"


def test_booking_defaults_to_pending_status(db_session):
    booking = Booking(
        id=str(uuid4()),
        candidate_name="Test Candidate",
        email="candidate@example.com",
        interview_at=datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc),
    )

    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)

    assert booking.status == "pending"


def test_booking_rejects_invalid_status(db_session):
    booking = Booking(
        id=str(uuid4()),
        candidate_name="Test Candidate",
        email="candidate@example.com",
        interview_at=datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc),
        status="invalid",
    )

    db_session.add(booking)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_booking_rejects_missing_required_fields(db_session):
    booking = Booking(
        id=str(uuid4()),
        candidate_name="Test Candidate",
        interview_at=datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc),
    )

    db_session.add(booking)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_booking_stores_interview_timestamp(db_session):
    interview_at = datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc)

    booking = Booking(
        id=str(uuid4()),
        candidate_name="Test Candidate",
        email="candidate@example.com",
        interview_at=interview_at,
    )

    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)

    assert booking.interview_at.replace(tzinfo=timezone.utc) == interview_at

def test_duplicate_active_interview_time_is_rejected(db_session):
    from datetime import datetime, timedelta, timezone
    from uuid import uuid4

    from sqlalchemy.exc import IntegrityError

    interview_at = datetime.now(timezone.utc) + timedelta(days=3)

    first_booking = Booking(
        id=str(uuid4()),
        candidate_name="Candidate One",
        email="one@example.com",
        interview_at=interview_at,
    )

    second_booking = Booking(
        id=str(uuid4()),
        candidate_name="Candidate Two",
        email="two@example.com",
        interview_at=interview_at,
    )

    db_session.add(first_booking)
    db_session.commit()

    db_session.add(second_booking)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_cancelled_booking_releases_interview_time(db_session):
    from datetime import datetime, timedelta, timezone
    from uuid import uuid4

    interview_at = datetime.now(timezone.utc) + timedelta(days=3)

    first_booking = Booking(
        id=str(uuid4()),
        candidate_name="Candidate One",
        email="one@example.com",
        interview_at=interview_at,
    )

    db_session.add(first_booking)
    db_session.commit()

    first_booking.status = "cancelled"
    db_session.commit()

    second_booking = Booking(
        id=str(uuid4()),
        candidate_name="Candidate Two",
        email="two@example.com",
        interview_at=interview_at,
    )

    db_session.add(second_booking)
    db_session.commit()

    assert second_booking.id is not None
    assert second_booking.status == "pending"


def test_pending_booking_reserves_interview_time(db_session):
    from datetime import datetime, timedelta, timezone
    from uuid import uuid4

    from sqlalchemy.exc import IntegrityError

    interview_at = datetime.now(timezone.utc) + timedelta(days=3)

    first_booking = Booking(
        id=str(uuid4()),
        candidate_name="Candidate One",
        email="one@example.com",
        interview_at=interview_at,
        status="pending",
    )

    second_booking = Booking(
        id=str(uuid4()),
        candidate_name="Candidate Two",
        email="two@example.com",
        interview_at=interview_at,
        status="confirmed",
    )

    db_session.add(first_booking)
    db_session.commit()

    db_session.add(second_booking)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()
