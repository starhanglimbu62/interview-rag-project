from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.booking_conversation import (
    BookingConversationRequest,
    BookingConversationResponse,
)
from app.schemas.booking_extraction import BookingExtraction


def test_valid_booking_conversation_request():
    request = BookingConversationRequest(
        message="My name is Test Candidate.",
    )

    assert request.message == "My name is Test Candidate."
    assert request.conversation_id is None
    assert request.confirm_booking is False


def test_trims_message():
    request = BookingConversationRequest(
        message="  Book an interview  ",
    )

    assert request.message == "Book an interview"


def test_rejects_empty_message():
    with pytest.raises(ValidationError):
        BookingConversationRequest(message="   ")


def test_rejects_unexpected_fields():
    with pytest.raises(ValidationError):
        BookingConversationRequest(
            message="Book an interview",
            status="confirmed",
        )


def test_accepts_confirmation_flag():
    request = BookingConversationRequest(
        message="I confirm the booking.",
        confirm_booking=True,
    )

    assert request.confirm_booking is True


def test_generates_conversation_response():
    conversation_id = uuid4()

    response = BookingConversationResponse(
        conversation_id=conversation_id,
        message="Please provide your email address.",
        status="collecting_details",
        missing_fields=["email", "interview_at"],
    )

    assert response.conversation_id == conversation_id
    assert response.status == "collecting_details"
    assert "email" in response.missing_fields
    assert response.booking is None


def test_response_supports_booking_details():
    details = BookingExtraction(
        candidate_name="Test Candidate",
        email="test@example.com",
        interview_at=datetime.now(timezone.utc) + timedelta(days=5),
    )

    response = BookingConversationResponse(
        conversation_id=uuid4(),
        message="Please confirm your booking.",
        status="awaiting_confirmation",
        booking_details=details,
    )

    assert response.booking_details == details


def test_rejects_invalid_status():
    with pytest.raises(ValidationError):
        BookingConversationResponse(
            conversation_id=uuid4(),
            message="Invalid status",
            status="processing",
        )
