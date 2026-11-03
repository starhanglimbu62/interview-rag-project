import json
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.services.chat_memory import RedisChatMemory


@pytest.fixture
def redis_client():
    return MagicMock()


@pytest.fixture
def memory(redis_client):
    return RedisChatMemory(
        client=redis_client,
        ttl_seconds=3600,
        max_messages=10,
    )


def test_get_history_returns_messages_in_order(memory, redis_client):
    conversation_id = uuid4()

    redis_client.lrange.return_value = [
        json.dumps({"role": "user", "content": "Hello"}),
        json.dumps({"role": "assistant", "content": "Hi"}),
    ]

    history = memory.get_history(conversation_id)

    assert history == [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"},
    ]

    redis_client.lrange.assert_called_once_with(
        f"chat:conversation:{conversation_id}:messages",
        0,
        -1,
    )


def test_get_history_returns_empty_list(memory, redis_client):
    redis_client.lrange.return_value = []

    assert memory.get_history(uuid4()) == []


def test_add_message_stores_message(memory, redis_client):
    conversation_id = uuid4()
    pipeline = redis_client.pipeline.return_value

    memory.add_message(conversation_id, "user", "  Hello  ")

    key = f"chat:conversation:{conversation_id}:messages"

    redis_client.pipeline.assert_called_once_with(transaction=True)
    pipeline.rpush.assert_called_once_with(
        key,
        json.dumps({"role": "user", "content": "Hello"}),
    )
    pipeline.ltrim.assert_called_once_with(key, -10, -1)
    pipeline.expire.assert_called_once_with(key, 3600)
    pipeline.execute.assert_called_once()


def test_add_assistant_message(memory, redis_client):
    pipeline = redis_client.pipeline.return_value

    memory.add_message(uuid4(), "assistant", "Hello")

    stored_message = pipeline.rpush.call_args.args[1]

    assert json.loads(stored_message) == {
        "role": "assistant",
        "content": "Hello",
    }


def test_reject_invalid_role(memory):
    with pytest.raises(ValueError, match="Role must be user or assistant"):
        memory.add_message(uuid4(), "system", "Invalid role")


@pytest.mark.parametrize("content", ["", "   ", "\n"])
def test_reject_empty_message(memory, content):
    with pytest.raises(ValueError, match="Message content cannot be empty"):
        memory.add_message(uuid4(), "user", content)


def test_reject_invalid_ttl(redis_client):
    with pytest.raises(ValueError, match="TTL must be greater than zero"):
        RedisChatMemory(client=redis_client, ttl_seconds=0)


def test_reject_invalid_history_limit(redis_client):
    with pytest.raises(ValueError, match="Maximum messages must be greater than zero"):
        RedisChatMemory(client=redis_client, max_messages=0)


def test_reject_corrupted_history(memory, redis_client):
    redis_client.lrange.return_value = ["not-valid-json"]

    with pytest.raises(RuntimeError, match="Stored conversation history is corrupted"):
        memory.get_history(uuid4())

def test_get_history_rejects_invalid_role(memory, redis_client):
    redis_client.lrange.return_value = [
        json.dumps({"role": "system", "content": "Invalid"})
    ]

    with pytest.raises(RuntimeError, match="contains invalid messages"):
        memory.get_history(uuid4())


def test_get_history_rejects_invalid_message_structure(memory, redis_client):
    redis_client.lrange.return_value = [
        json.dumps({"role": "user"})
    ]

    with pytest.raises(RuntimeError, match="contains invalid messages"):
        memory.get_history(uuid4())


def test_get_history_rejects_non_dictionary_message(memory, redis_client):
    redis_client.lrange.return_value = [
        json.dumps(["user", "Hello"])
    ]

    with pytest.raises(RuntimeError, match="contains invalid messages"):
        memory.get_history(uuid4())
