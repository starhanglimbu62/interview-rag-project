import json
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from app.schemas.booking_extraction import BookingExtraction
from app.services.booking_extraction_service import (
    BookingExtractionService,
)


def create_service(response):
    llm = Mock()
    llm.generate.return_value = response

    return BookingExtractionService(llm), llm


def test_extracts_complete_booking_details():
    interview_at = (
        datetime.now(timezone.utc) + timedelta(days=3)
    ).isoformat()

    response = json.dumps({
        "candidate_name": "Test Candidate",
        "email": "test@example.com",
        "interview_at": interview_at,
    })

    service, llm = create_service(response)

    result = service.extract("I want to book an interview.")

    assert result.candidate_name == "Test Candidate"
    assert result.email == "test@example.com"
    assert result.interview_at is not None

    llm.generate.assert_called_once()


def test_extracts_partial_booking_details():
    service, _ = create_service(json.dumps({
        "candidate_name": "Test Candidate",
        "email": None,
        "interview_at": None,
    }))

    result = service.extract("My name is Test Candidate.")

    assert result.candidate_name == "Test Candidate"
    assert result.email is None
    assert result.interview_at is None


def test_preserves_existing_details():
    existing = BookingExtraction(
        candidate_name="Test Candidate",
        email="test@example.com",
    )

    service, _ = create_service(json.dumps({
        "candidate_name": None,
        "email": None,
        "interview_at": None,
    }))

    result = service.extract(
        "I would like to continue.",
        existing,
    )

    assert result.candidate_name == "Test Candidate"
    assert result.email == "test@example.com"


def test_updates_existing_details():
    existing = BookingExtraction(
        candidate_name="Old Name",
        email="old@example.com",
    )

    service, _ = create_service(json.dumps({
        "candidate_name": "New Name",
        "email": None,
        "interview_at": None,
    }))

    result = service.extract(
        "My correct name is New Name.",
        existing,
    )

    assert result.candidate_name == "New Name"
    assert result.email == "old@example.com"


def test_rejects_empty_message():
    service, llm = create_service("{}")

    with pytest.raises(ValueError, match="Message cannot be empty"):
        service.extract("   ")

    llm.generate.assert_not_called()


def test_rejects_invalid_json():
    service, _ = create_service("This is not JSON")

    with pytest.raises(ValueError, match="invalid JSON"):
        service.extract("I want to book an interview.")


def test_rejects_non_object_json():
    service, _ = create_service('["candidate", "email"]')

    with pytest.raises(ValueError, match="JSON object"):
        service.extract("I want to book an interview.")


def test_rejects_invalid_extracted_email():
    service, _ = create_service(json.dumps({
        "candidate_name": "Test Candidate",
        "email": "invalid-email",
        "interview_at": None,
    }))

    with pytest.raises(ValueError):
        service.extract("My email is invalid-email.")


def test_rejects_naive_extracted_datetime():
    service, _ = create_service(json.dumps({
        "candidate_name": None,
        "email": None,
        "interview_at": "2026-12-01T10:00:00",
    }))

    with pytest.raises(ValueError):
        service.extract("Book me for December 1 at 10 AM.")


def test_rejects_unexpected_extraction_fields():
    service, _ = create_service(json.dumps({
        "candidate_name": "Test Candidate",
        "email": None,
        "interview_at": None,
        "status": "confirmed",
    }))

    with pytest.raises(ValueError):
        service.extract("My name is Test Candidate.")


def test_passes_existing_details_to_llm():
    existing = BookingExtraction(
        candidate_name="Test Candidate",
    )

    service, llm = create_service(json.dumps({
        "candidate_name": None,
        "email": "test@example.com",
        "interview_at": None,
    }))

    service.extract("My email is test@example.com.", existing)

    messages = llm.generate.call_args.args[0]

    assert "Test Candidate" in messages[1]["content"]
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
