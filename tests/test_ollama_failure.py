import httpx
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.database import Base
from app.main import app
from app.models import Booking
from app.routes.bookings import get_booking_state
from app.routes.chat import get_llm_service
from app.services.llm_service import LLMService
from app.services.booking_state import RedisBookingState


class FakeRedis:
    """In-memory Redis substitute for isolated tests."""

    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex=None):
        self.data[key] = value
        return True

    def delete(self, *keys):
        deleted = 0
        for key in keys:
            if key in self.data:
                del self.data[key]
                deleted += 1
        return deleted


def test_llm_service_propagates_ollama_connection_error():
    """Verify that an Ollama connection failure is propagated."""

    def fail_connection(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(
            "Ollama is unavailable",
            request=request,
        )

    transport = httpx.MockTransport(fail_connection)

    with httpx.Client(
        transport=transport,
        base_url="http://ollama-test",
    ) as client:
        llm_service = LLMService(client=client)

        with pytest.raises(httpx.ConnectError):
            llm_service.generate([
                {
                    "role": "user",
                    "content": "Extract the booking details.",
                }
            ])


def test_booking_endpoint_handles_real_llm_connection_failure(
    db_session,
    monkeypatch,
):
    """
    Exercise the complete booking dependency chain.

    The real LLMService raises a simulated connection error.
    The route must return HTTP 503 without creating a booking.
    """

    def fail_connection(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(
            "Simulated Ollama outage",
            request=request,
        )

    transport = httpx.MockTransport(fail_connection)
    http_client = httpx.Client(
        transport=transport,
        base_url="http://ollama-test",
    )

    llm_service = LLMService(client=http_client)
    redis_state = RedisBookingState(client=FakeRedis())

    monkeypatch.setitem(
        app.dependency_overrides,
        get_llm_service,
        lambda: llm_service,
    )

    monkeypatch.setitem(
        app.dependency_overrides,
        get_booking_state,
        lambda: redis_state,
    )

    try:
        count_before = db_session.scalar(
            select(func.count()).select_from(Booking)
        )

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/bookings/conversation",
                json={
                    "message": (
                        "My name is Test Candidate and my email is "
                        "test-candidate@example.com."
                    )
                },
            )

        count_after = db_session.scalar(
            select(func.count()).select_from(Booking)
        )

        assert response.status_code == 503
        assert response.json()["detail"] == (
            "A required service is temporarily unavailable"
        )
        assert count_after == count_before

    finally:
        http_client.close()
