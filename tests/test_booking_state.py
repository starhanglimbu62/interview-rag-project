import json
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.schemas.booking_extraction import BookingExtraction
from app.services.booking_state import RedisBookingState


@pytest.fixture
def redis_client():
    return Mock()


@pytest.fixture
def booking_state(redis_client):
    return RedisBookingState(client=redis_client, ttl_seconds=3600)


@pytest.fixture
def conversation_id():
    return uuid4()


@pytest.fixture
def sample_state():
    return BookingExtraction(
        candidate_name="Test Candidate",
        email="test@example.com",
        interview_at=datetime.now(timezone.utc) + timedelta(days=5),
    )


def test_returns_none_when_state_does_not_exist(
    booking_state, redis_client, conversation_id
):
    redis_client.get.return_value = None

    assert booking_state.get_state(conversation_id) is None


def test_saves_booking_state(
    booking_state, redis_client, conversation_id, sample_state
):
    booking_state.save_state(conversation_id, sample_state)

    redis_client.set.assert_called_once_with(
        f"chat:conversation:{conversation_id}:booking",
        sample_state.model_dump_json(),
        ex=3600,
    )

    redis_client.delete.assert_called_once_with(
        f"chat:conversation:{conversation_id}:booking:confirmation"
    )


def test_retrieves_booking_state(
    booking_state, redis_client, conversation_id, sample_state
):
    redis_client.get.return_value = sample_state.model_dump_json()

    result = booking_state.get_state(conversation_id)

    assert result == sample_state


def test_retrieves_booking_state_from_bytes(
    booking_state, redis_client, conversation_id, sample_state
):
    redis_client.get.return_value = sample_state.model_dump_json().encode()

    result = booking_state.get_state(conversation_id)

    assert result == sample_state


def test_rejects_corrupted_booking_state(
    booking_state, redis_client, conversation_id
):
    redis_client.get.return_value = "not valid JSON"

    with pytest.raises(RuntimeError, match="corrupted or invalid"):
        booking_state.get_state(conversation_id)


def test_rejects_invalid_booking_state(
    booking_state, redis_client, conversation_id
):
    redis_client.get.return_value = json.dumps({
        "candidate_name": "Test Candidate",
        "email": "invalid-email",
        "interview_at": None,
    })

    with pytest.raises(RuntimeError, match="corrupted or invalid"):
        booking_state.get_state(conversation_id)


def test_marks_booking_as_awaiting_confirmation(
    booking_state, redis_client, conversation_id, sample_state
):
    redis_client.get.return_value = sample_state.model_dump_json()

    booking_state.mark_awaiting_confirmation(conversation_id)

    redis_client.set.assert_called_once_with(
        f"chat:conversation:{conversation_id}:booking:confirmation",
        booking_state._get_fingerprint(sample_state),
        ex=3600,
    )


def test_rejects_confirmation_without_booking_details(
    booking_state, redis_client, conversation_id
):
    redis_client.get.return_value = None

    with pytest.raises(ValueError, match="missing booking details"):
        booking_state.mark_awaiting_confirmation(conversation_id)


def test_checks_confirmation_marker(
    booking_state, redis_client, conversation_id, sample_state
):
    redis_client.get.side_effect = [
        sample_state.model_dump_json(),
        booking_state._get_fingerprint(sample_state),
    ]

    assert booking_state.is_awaiting_confirmation(conversation_id) is True


def test_returns_false_without_confirmation_marker(
    booking_state, redis_client, conversation_id, sample_state
):
    redis_client.get.side_effect = [
        sample_state.model_dump_json(),
        None,
    ]

    assert booking_state.is_awaiting_confirmation(conversation_id) is False


def test_rejects_stale_confirmation(
    booking_state, redis_client, conversation_id, sample_state
):
    changed_state = sample_state.model_copy(
        update={"candidate_name": "Different Candidate"}
    )

    redis_client.get.side_effect = [
        changed_state.model_dump_json(),
        booking_state._get_fingerprint(sample_state),
    ]

    assert booking_state.is_awaiting_confirmation(conversation_id) is False


def test_clears_both_booking_keys(
    booking_state, redis_client, conversation_id
):
    booking_state.clear_state(conversation_id)

    redis_client.delete.assert_called_once_with(
        f"chat:conversation:{conversation_id}:booking",
        f"chat:conversation:{conversation_id}:booking:confirmation",
    )


def test_rejects_invalid_ttl():
    with pytest.raises(ValueError, match="TTL"):
        RedisBookingState(client=Mock(), ttl_seconds=0)


def test_rejects_wrong_state_type(
    booking_state, conversation_id
):
    with pytest.raises(TypeError, match="BookingExtraction"):
        booking_state.save_state(
            conversation_id,
            {"candidate_name": "Test"},
        )


def test_uses_separate_key_from_chat_history(conversation_id):
    booking_key = RedisBookingState._get_key(conversation_id)
    chat_key = f"chat:conversation:{conversation_id}:messages"

    assert booking_key != chat_key
