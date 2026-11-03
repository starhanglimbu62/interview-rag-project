import pytest
import redis

from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.routes.chat import get_rag_service, get_chat_memory


class FakeRAGService:
    def __init__(self):
        self.calls = []
        self.should_fail = False

    def answer(self, question, document_id=None, history=None):
        self.calls.append({
            "question": question,
            "document_id": document_id,
            "history": history or [],
        })

        if self.should_fail:
            raise RuntimeError("Simulated RAG failure")

        return {
            "answer": "Employees receive 15 days of annual leave. [S1]",
            "sources": [{
                "source_id": "S1",
                "document_id": "doc-123",
                "filename": "company_policy.pdf",
                "chunk_index": 2,
                "score": 0.89,
            }],
        }


class FakeChatMemory:
    def __init__(self):
        self.conversations = {}
        self.should_fail = False

    def get_history(self, conversation_id):
        if self.should_fail:
            raise redis.RedisError("Simulated Redis failure")

        history = self.conversations.get(str(conversation_id), [])
        return [message.copy() for message in history]

    def add_message(self, conversation_id, role, content):
        if self.should_fail:
            raise redis.RedisError("Simulated Redis failure")

        key = str(conversation_id)
        self.conversations.setdefault(key, []).append({
            "role": role,
            "content": content,
        })


@pytest.fixture
def fake_rag_service():
    return FakeRAGService()


@pytest.fixture
def fake_chat_memory():
    return FakeChatMemory()


@pytest.fixture
def client(fake_rag_service, fake_chat_memory):
    app.dependency_overrides[get_rag_service] = lambda: fake_rag_service
    app.dependency_overrides[get_chat_memory] = lambda: fake_chat_memory

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_rag_service, None)
    app.dependency_overrides.pop(get_chat_memory, None)


def test_chat_returns_answer_and_sources(client):
    response = client.post(
        "/api/v1/chat",
        json={"question": "How many annual leave days are provided?"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["answer"] == "Employees receive 15 days of annual leave. [S1]"
    assert data["sources"][0]["filename"] == "company_policy.pdf"
    assert data["conversation_id"]


def test_chat_passes_question_to_rag_service(client, fake_rag_service):
    question = "How many annual leave days are provided?"

    response = client.post(
        "/api/v1/chat",
        json={"question": question},
    )

    assert response.status_code == 200
    assert fake_rag_service.calls[0]["question"] == question


def test_chat_passes_document_id_to_rag_service(client, fake_rag_service):
    document_id = str(uuid4())

    response = client.post(
        "/api/v1/chat",
        json={
            "question": "Summarize this document",
            "document_id": document_id,
        },
    )

    assert response.status_code == 200
    assert fake_rag_service.calls[0]["document_id"] == document_id


def test_chat_rejects_empty_question(client):
    response = client.post(
        "/api/v1/chat",
        json={"question": "   "},
    )

    assert response.status_code == 422


def test_chat_rejects_missing_question(client):
    response = client.post("/api/v1/chat", json={})

    assert response.status_code == 422


def test_chat_rejects_invalid_document_id(client):
    response = client.post(
        "/api/v1/chat",
        json={
            "question": "Hello",
            "document_id": "invalid-id",
        },
    )

    assert response.status_code == 422


def test_chat_rejects_unexpected_fields(client):
    response = client.post(
        "/api/v1/chat",
        json={
            "question": "Hello",
            "unexpected": "value",
        },
    )

    assert response.status_code == 422


def test_chat_handles_internal_errors(client, fake_rag_service):
    fake_rag_service.should_fail = True

    response = client.post(
        "/api/v1/chat",
        json={"question": "Hello"},
    )

    assert response.status_code == 500


def test_new_conversation_generates_id(client):
    response = client.post(
        "/api/v1/chat",
        json={"question": "Hello"},
    )

    assert response.status_code == 200
    assert response.json()["conversation_id"]


def test_existing_conversation_id_is_reused(client):
    conversation_id = str(uuid4())

    response = client.post(
        "/api/v1/chat",
        json={
            "question": "Hello",
            "conversation_id": conversation_id,
        },
    )

    assert response.status_code == 200
    assert response.json()["conversation_id"] == conversation_id


def test_follow_up_receives_previous_history(
    client,
    fake_rag_service,
):
    conversation_id = str(uuid4())

    first_response = client.post(
        "/api/v1/chat",
        json={
            "question": "How many annual leave days are provided?",
            "conversation_id": conversation_id,
        },
    )

    assert first_response.status_code == 200

    second_response = client.post(
        "/api/v1/chat",
        json={
            "question": "Can you explain that?",
            "conversation_id": conversation_id,
        },
    )

    assert second_response.status_code == 200

    history = fake_rag_service.calls[1]["history"]

    assert history == [
        {
            "role": "user",
            "content": "How many annual leave days are provided?",
        },
        {
            "role": "assistant",
            "content": "Employees receive 15 days of annual leave. [S1]",
        },
    ]


def test_conversations_have_isolated_histories(
    client,
    fake_rag_service,
):
    conversation_one = str(uuid4())
    conversation_two = str(uuid4())

    client.post(
        "/api/v1/chat",
        json={
            "question": "Question one",
            "conversation_id": conversation_one,
        },
    )

    client.post(
        "/api/v1/chat",
        json={
            "question": "Question two",
            "conversation_id": conversation_two,
        },
    )

    assert fake_rag_service.calls[0]["history"] == []
    assert fake_rag_service.calls[1]["history"] == []


def test_successful_chat_saves_user_and_assistant_messages(
    client,
    fake_chat_memory,
):
    conversation_id = str(uuid4())

    response = client.post(
        "/api/v1/chat",
        json={
            "question": "How many leave days?",
            "conversation_id": conversation_id,
        },
    )

    assert response.status_code == 200

    assert fake_chat_memory.conversations[conversation_id] == [
        {
            "role": "user",
            "content": "How many leave days?",
        },
        {
            "role": "assistant",
            "content": "Employees receive 15 days of annual leave. [S1]",
        },
    ]


def test_redis_failure_returns_service_unavailable(
    client,
    fake_chat_memory,
):
    fake_chat_memory.should_fail = True

    response = client.post(
        "/api/v1/chat",
        json={"question": "Hello"},
    )

    assert response.status_code == 503
