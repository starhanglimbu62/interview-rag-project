from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.schemas.booking import BookingRequest


def future_datetime():
    return datetime.now(timezone.utc) + timedelta(days=2)


def valid_payload():
    return {
        "candidate_name": "Test Candidate",
        "email": "Candidate@Example.com",
        "interview_at": future_datetime(),
    }


def test_valid_booking_request():
    booking = BookingRequest(**valid_payload())

    assert booking.candidate_name == "Test Candidate"
    assert booking.email == "candidate@example.com"
    assert booking.interview_at.tzinfo is not None


def test_candidate_name_is_trimmed():
    payload = valid_payload()
    payload["candidate_name"] = "  Test Candidate  "

    booking = BookingRequest(**payload)

    assert booking.candidate_name == "Test Candidate"


@pytest.mark.parametrize("name", ["", " ", "A"])
def test_reject_invalid_candidate_name(name):
    payload = valid_payload()
    payload["candidate_name"] = name

    with pytest.raises(ValidationError):
        BookingRequest(**payload)


def test_reject_invalid_email():
    payload = valid_payload()
    payload["email"] = "invalid-email"

    with pytest.raises(ValidationError):
        BookingRequest(**payload)


def test_email_is_normalized():
    payload = valid_payload()
    payload["email"] = "Candidate@Example.com"

    booking = BookingRequest(**payload)

    assert booking.email == "candidate@example.com"


def test_reject_naive_datetime():
    payload = valid_payload()
    payload["interview_at"] = datetime.now() + timedelta(days=2)

    with pytest.raises(ValidationError, match="must include a timezone"):
        BookingRequest(**payload)


def test_reject_past_datetime():
    payload = valid_payload()
    payload["interview_at"] = datetime.now(timezone.utc) - timedelta(days=1)

    with pytest.raises(ValidationError, match="must be in the future"):
        BookingRequest(**payload)


def test_accept_nepal_timezone():
    payload = valid_payload()
    payload["interview_at"] = (
        datetime.now(timezone.utc) + timedelta(days=2)
    ).astimezone(
        timezone(timedelta(hours=5, minutes=45))
    )

    booking = BookingRequest(**payload)

    assert booking.interview_at.utcoffset() == timedelta(hours=5, minutes=45)


def test_reject_unexpected_fields():
    payload = valid_payload()
    payload["status"] = "confirmed"

    with pytest.raises(ValidationError):
        BookingRequest(**payload)
