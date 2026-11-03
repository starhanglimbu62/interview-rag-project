import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes.chat import get_rag_service


class FakeRAGService:
    def __init__(self):
        self.calls = []
        self.should_fail = False

    def answer(self, question, document_id=None):
        self.calls.append({
            "question": question,
            "document_id": document_id
        })

        if self.should_fail:
            raise RuntimeError("Simulated RAG failure")

        return {
            "answer": "Employees receive 15 days of annual leave. [S1]",
            "sources": [
                {
                    "source_id": "S1",
                    "document_id": "doc-123",
                    "filename": "company_policy.pdf",
                    "chunk_index": 2,
                    "score": 0.89
                }
            ]
        }


@pytest.fixture
def fake_rag_service():
    return FakeRAGService()


@pytest.fixture
def client(fake_rag_service):
    app.dependency_overrides[get_rag_service] = lambda: fake_rag_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_rag_service, None)


def test_chat_returns_answer_and_sources(client):
    response = client.post(
        "/api/v1/chat",
        json={"question": "What is the annual leave policy?"}
    )

    assert response.status_code == 200

    data = response.json()

    assert data["answer"] == (
        "Employees receive 15 days of annual leave. [S1]"
    )
    assert len(data["sources"]) == 1
    assert data["sources"][0]["filename"] == "company_policy.pdf"


def test_chat_passes_question_to_rag_service(
    client,
    fake_rag_service
):
    question = "How many annual leave days are provided?"

    client.post(
        "/api/v1/chat",
        json={"question": question}
    )

    assert fake_rag_service.calls[0]["question"] == question


def test_chat_passes_document_id_to_rag_service(
    client,
    fake_rag_service
):
    client.post(
        "/api/v1/chat",
        json={
            "question": "What is the policy?",
            "document_id": "12345678-1234-5678-1234-567812345678"
        }
    )

    assert fake_rag_service.calls[0]["document_id"] == (
        "12345678-1234-5678-1234-567812345678"
    )


def test_chat_rejects_empty_question(client):
    response = client.post(
        "/api/v1/chat",
        json={"question": "   "}
    )

    assert response.status_code == 422


def test_chat_rejects_missing_question(client):
    response = client.post(
        "/api/v1/chat",
        json={}
    )

    assert response.status_code == 422


def test_chat_rejects_invalid_document_id(client):
    response = client.post(
        "/api/v1/chat",
        json={
            "question": "What is the policy?",
            "document_id": "not-a-valid-uuid"
        }
    )

    assert response.status_code == 422


def test_chat_rejects_unexpected_fields(client):
    response = client.post(
        "/api/v1/chat",
        json={
            "question": "What is the policy?",
            "unexpected": "value"
        }
    )

    assert response.status_code == 422


def test_chat_handles_internal_errors(
    client,
    fake_rag_service
):
    fake_rag_service.should_fail = True

    response = client.post(
        "/api/v1/chat",
        json={"question": "What is the policy?"}
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Unable to process chat request"
