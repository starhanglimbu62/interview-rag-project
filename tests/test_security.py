from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.routes.chat import get_chat_memory, get_rag_service


class FakeRAGService:
    def answer(self, question, document_id=None, history=None):
        return {"answer": "ok", "sources": []}


class FakeChatMemory:
    def get_history(self, conversation_id):
        return []

    def add_message(self, conversation_id, role, content):
        return None


def _client():
    app.dependency_overrides[get_rag_service] = lambda: FakeRAGService()
    app.dependency_overrides[get_chat_memory] = lambda: FakeChatMemory()
    return TestClient(app)


def test_api_key_is_not_required_in_development_without_configuration(
    monkeypatch,
):
    monkeypatch.setattr(settings, "api_key", None)
    monkeypatch.setattr(settings, "app_env", "development")

    with _client() as client:
        response = client.post(
            "/api/v1/chat",
            json={"question": "hello"},
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200


def test_api_key_protects_api_routes(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "test-api-key")
    monkeypatch.setattr(settings, "app_env", "development")

    with _client() as client:
        missing = client.post(
            "/api/v1/chat",
            json={"question": "hello"},
        )
        invalid = client.post(
            "/api/v1/chat",
            headers={"X-API-Key": "wrong"},
            json={"question": "hello"},
        )

    app.dependency_overrides.clear()
    assert missing.status_code == 401
    assert invalid.status_code == 401


def test_valid_api_key_allows_api_route(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "test-api-key")
    monkeypatch.setattr(settings, "app_env", "development")

    with _client() as client:
        response = client.post(
            "/api/v1/chat",
            headers={"X-API-Key": "test-api-key"},
            json={"question": "hello"},
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200


def test_health_remains_public_when_api_key_is_configured(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "test-api-key")

    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
