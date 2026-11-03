from types import SimpleNamespace

import pytest

from app.services.llm_service import LLMService


class FakeResponse:
    def __init__(self, content="Generated answer"):
        self.content = content

    def raise_for_status(self):
        pass

    def json(self):
        return {
            "message": {
                "content": self.content
            }
        }


class FakeClient:
    def __init__(self, content="Generated answer"):
        self.response = FakeResponse(content)
        self.called_url = None
        self.called_json = None

    def post(self, url, json):
        self.called_url = url
        self.called_json = json
        return self.response


def test_generate_returns_response():
    client = FakeClient("This is the generated answer.")
    service = LLMService(client=client)

    result = service.generate([
        {"role": "user", "content": "What is Python?"}
    ])

    assert result == "This is the generated answer."


def test_generate_strips_whitespace():
    service = LLMService(client=FakeClient("  Answer  "))

    result = service.generate([
        {"role": "user", "content": "Question"}
    ])

    assert result == "Answer"


def test_generate_calls_ollama_chat_endpoint():
    client = FakeClient()
    service = LLMService(client=client)

    service.generate([
        {"role": "user", "content": "Explain RAG."}
    ])

    assert client.called_url == "/api/chat"


def test_generate_sends_correct_payload():
    client = FakeClient()
    service = LLMService(client=client)

    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Explain RAG."}
    ]

    service.generate(messages)

    assert client.called_json["model"] == service.model
    assert client.called_json["messages"] == messages
    assert client.called_json["stream"] is False
    assert client.called_json["think"] is False
    assert client.called_json["options"]["temperature"] == 0.2


def test_reject_empty_messages():
    service = LLMService(client=FakeClient())

    with pytest.raises(ValueError, match="Messages cannot be empty"):
        service.generate([])


def test_reject_invalid_role():
    service = LLMService(client=FakeClient())

    with pytest.raises(ValueError, match="Invalid message role"):
        service.generate([
            {"role": "developer", "content": "Invalid role"}
        ])


def test_reject_empty_message_content():
    service = LLMService(client=FakeClient())

    with pytest.raises(ValueError, match="Message content cannot be empty"):
        service.generate([
            {"role": "user", "content": "   "}
        ])


def test_reject_empty_llm_response():
    service = LLMService(client=FakeClient("   "))

    with pytest.raises(RuntimeError, match="empty response"):
        service.generate([
            {"role": "user", "content": "Question"}
        ])