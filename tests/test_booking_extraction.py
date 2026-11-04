from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.schemas.booking_extraction import BookingExtraction


def test_accepts_empty_extraction():
    result = BookingExtraction()

    assert result.candidate_name is None
    assert result.email is None
    assert result.interview_at is None


def test_accepts_partial_extraction():
    result = BookingExtraction(
        candidate_name="Test Candidate",
    )

    assert result.candidate_name == "Test Candidate"
    assert result.email is None
    assert result.interview_at is None


def test_normalizes_candidate_name():
    result = BookingExtraction(
        candidate_name="  Test Candidate  ",
    )

    assert result.candidate_name == "Test Candidate"


def test_empty_candidate_name_becomes_none():
    result = BookingExtraction(
        candidate_name="   ",
    )

    assert result.candidate_name is None


def test_normalizes_email():
    result = BookingExtraction(
        email="Candidate@Example.com",
    )

    assert result.email == "candidate@example.com"


def test_rejects_invalid_email():
    with pytest.raises(ValidationError):
        BookingExtraction(email="invalid-email")


def test_accepts_timezone_aware_datetime():
    interview_at = (
        datetime.now(timezone.utc) + timedelta(days=2)
    )

    result = BookingExtraction(interview_at=interview_at)

    assert result.interview_at == interview_at


def test_rejects_naive_datetime():
    interview_at = datetime.now() + timedelta(days=2)

    with pytest.raises(
        ValidationError,
        match="must include a timezone",
    ):
        BookingExtraction(interview_at=interview_at)


def test_rejects_unexpected_fields():
    with pytest.raises(ValidationError):
        BookingExtraction(
            candidate_name="Test Candidate",
            status="confirmed",
        )
