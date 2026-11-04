from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import Mock

import pytest

from app.schemas.booking import BookingRequest
from app.schemas.booking_conversation import BookingConversationRequest
from app.schemas.booking_extraction import BookingExtraction
from app.services.booking_service import BookingSlotUnavailableError
from app.services.booking_conversation_service import (
    BookingConversationService,
)


@pytest.fixture
def conversation_id():
    return uuid4()


@pytest.fixture
def complete_details():
    return BookingExtraction(
        candidate_name="Star Limbu",
        email="star@example.com",
        interview_at=datetime.now(timezone.utc) + timedelta(days=7),
    )


@pytest.fixture
def service():
    extraction = Mock()
    state_store = Mock()
    booking_service = Mock()

    return BookingConversationService(
        extraction_service=extraction,
        state_store=state_store,
        booking_service=booking_service,
    )


def test_requests_missing_booking_details(
    service,
    conversation_id,
):
    service.state_store.get_state.return_value = None
    service.extraction_service.extract.return_value = BookingExtraction(
        candidate_name="Star Limbu",
    )

    response = service.process(
        BookingConversationRequest(
            message="My name is Star Limbu",
            conversation_id=conversation_id,
        )
    )

    assert response.status == "collecting_details"
    assert response.missing_fields == ["email", "interview_at"]
    assert "email address" in response.message
    service.state_store.save_state.assert_called_once()


def test_returns_confirmation_summary_for_available_slot(
    service,
    conversation_id,
    complete_details,
):
    service.state_store.get_state.return_value = None
    service.extraction_service.extract.return_value = complete_details
    service.booking_service.is_slot_available.return_value = True

    response = service.process(
        BookingConversationRequest(
            message="Book my interview",
            conversation_id=conversation_id,
        )
    )

    assert response.status == "awaiting_confirmation"
    assert response.missing_fields == []
    assert "Star Limbu" in response.message
    assert "star@example.com" in response.message
    assert "Interview:" in response.message

    service.state_store.save_state.assert_called_once_with(
        conversation_id,
        complete_details,
    )
    service.state_store.mark_awaiting_confirmation.assert_called_once_with(
        conversation_id
    )


def test_does_not_mark_unavailable_slot_for_confirmation(
    service,
    conversation_id,
    complete_details,
):
    service.state_store.get_state.return_value = None
    service.extraction_service.extract.return_value = complete_details
    service.booking_service.is_slot_available.return_value = False

    response = service.process(
        BookingConversationRequest(
            message="Book my interview",
            conversation_id=conversation_id,
        )
    )

    assert response.status == "slot_unavailable"
    assert response.missing_fields == ["interview_at"]

    service.state_store.mark_awaiting_confirmation.assert_not_called()


def test_rejects_invalid_candidate_name(
    service,
    conversation_id,
):
    invalid_details = BookingExtraction(
        candidate_name="A",
        email="star@example.com",
        interview_at=datetime.now(timezone.utc) + timedelta(days=7),
    )

    service.state_store.get_state.return_value = None
    service.extraction_service.extract.return_value = invalid_details

    response = service.process(
        BookingConversationRequest(
            message="Book my interview",
            conversation_id=conversation_id,
        )
    )

    assert response.status == "collecting_details"
    assert response.missing_fields == ["candidate_name"]
    service.booking_service.is_slot_available.assert_not_called()


def test_rejects_confirmation_without_saved_details(
    service,
    conversation_id,
):
    service.state_store.get_state.return_value = None

    with pytest.raises(ValueError, match="No booking details"):
        service.process(
            BookingConversationRequest(
                message="I confirm",
                conversation_id=conversation_id,
                confirm_booking=True,
            )
        )

    service.extraction_service.extract.assert_not_called()


def test_rejects_confirmation_when_details_changed(
    service,
    conversation_id,
    complete_details,
):
    service.state_store.get_state.return_value = complete_details
    service.state_store.is_awaiting_confirmation.return_value = False

    with pytest.raises(ValueError, match="have changed"):
        service.process(
            BookingConversationRequest(
                message="I confirm",
                conversation_id=conversation_id,
                confirm_booking=True,
            )
        )

    service.booking_service.create_booking.assert_not_called()
    service.extraction_service.extract.assert_not_called()


def test_confirms_booking_and_clears_state(
    service,
    conversation_id,
    complete_details,
):
    service.state_store.get_state.return_value = complete_details
    service.state_store.is_awaiting_confirmation.return_value = True

    booking = SimpleNamespace(
        id=uuid4(),
        candidate_name=complete_details.candidate_name,
        email=str(complete_details.email),
        interview_at=complete_details.interview_at,
        status="confirmed",
        created_at=datetime.now(timezone.utc),
    )
    service.booking_service.create_booking.return_value = booking

    response = service.process(
        BookingConversationRequest(
            message="I confirm",
            conversation_id=conversation_id,
            confirm_booking=True,
        )
    )

    assert response.status == "confirmed"
    assert response.booking is not None
    assert response.booking.id == booking.id

    service.booking_service.create_booking.assert_called_once()
    service.state_store.clear_state.assert_called_once_with(
        conversation_id
    )
    service.extraction_service.extract.assert_not_called()


def test_rechecks_slot_during_confirmation(
    service,
    conversation_id,
    complete_details,
):
    service.state_store.get_state.return_value = complete_details
    service.state_store.is_awaiting_confirmation.return_value = True
    service.booking_service.create_booking.side_effect = BookingSlotUnavailableError(
        "The requested interview slot is no longer available"
    )

    response = service.process(
        BookingConversationRequest(
            message="I confirm",
            conversation_id=conversation_id,
            confirm_booking=True,
        )
    )

    assert response.status == "slot_unavailable"
    assert response.missing_fields == ["interview_at"]

    service.state_store.clear_state.assert_not_called()
    service.state_store.save_state.assert_called_once_with(
        conversation_id,
        complete_details,
    )
    service.extraction_service.extract.assert_not_called()


