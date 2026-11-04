from uuid import uuid4
from unittest.mock import Mock

import httpx
import pytest
import redis
from fastapi.testclient import TestClient

from app.main import app
from app.routes.bookings import get_booking_conversation_service
from app.schemas.booking_conversation import BookingConversationResponse


class FakeBookingConversationService:
    def __init__(self):
        self.calls = []
        self.response = BookingConversationResponse(
            conversation_id=uuid4(),
            message="Please provide your email address.",
            status="collecting_details",
            missing_fields=["email"],
        )
        self.error = None

    def process(self, request):
        self.calls.append(request)

        if self.error:
            raise self.error

        return self.response


@pytest.fixture
def fake_booking_service():
    return FakeBookingConversationService()


@pytest.fixture
def client(fake_booking_service):
    app.dependency_overrides[
        get_booking_conversation_service
    ] = lambda: fake_booking_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(
        get_booking_conversation_service,
        None,
    )


def test_booking_conversation_returns_response(client):
    response = client.post(
        "/api/v1/bookings/conversation",
        json={"message": "I want to book an interview"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "collecting_details"
    assert data["missing_fields"] == ["email"]
    assert data["conversation_id"]


def test_booking_conversation_passes_request_to_service(
    client,
    fake_booking_service,
):
    conversation_id = str(uuid4())

    response = client.post(
        "/api/v1/bookings/conversation",
        json={
            "message": "My name is Star Limbu",
            "conversation_id": conversation_id,
        },
    )

    assert response.status_code == 200
    assert len(fake_booking_service.calls) == 1

    request = fake_booking_service.calls[0]

    assert request.message == "My name is Star Limbu"
    assert str(request.conversation_id) == conversation_id


def test_booking_conversation_rejects_empty_message(client):
    response = client.post(
        "/api/v1/bookings/conversation",
        json={"message": "   "},
    )

    assert response.status_code == 422


def test_booking_conversation_rejects_missing_message(client):
    response = client.post(
        "/api/v1/bookings/conversation",
        json={},
    )

    assert response.status_code == 422


def test_booking_conversation_rejects_unexpected_fields(client):
    response = client.post(
        "/api/v1/bookings/conversation",
        json={
            "message": "Hello",
            "unexpected": "value",
        },
    )

    assert response.status_code == 422


def test_booking_conversation_maps_value_error_to_422(
    client,
    fake_booking_service,
):
    fake_booking_service.error = ValueError(
        "No booking details exist for this conversation"
    )

    response = client.post(
        "/api/v1/bookings/conversation",
        json={
            "message": "Confirm",
            "confirm_booking": True,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "No booking details exist for this conversation"
    )


@pytest.mark.parametrize(
    "error",
    [
        redis.RedisError("Redis unavailable"),
        httpx.ConnectError("Ollama unavailable"),
    ],
)
def test_booking_conversation_maps_infrastructure_errors_to_503(
    client,
    fake_booking_service,
    error,
):
    fake_booking_service.error = error

    response = client.post(
        "/api/v1/bookings/conversation",
        json={"message": "Hello"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "A required service is temporarily unavailable"
    )


def test_booking_conversation_maps_unexpected_errors_to_500(
    client,
    fake_booking_service,
):
    fake_booking_service.error = RuntimeError(
        "Unexpected internal failure"
    )

    response = client.post(
        "/api/v1/bookings/conversation",
        json={"message": "Hello"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Unable to process booking request"
    )
