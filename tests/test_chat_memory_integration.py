import os
import time
from uuid import uuid4

import pytest
import redis

from app.config import settings
from app.services.chat_memory import RedisChatMemory


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_REDIS_INTEGRATION") != "1",
    reason="Set RUN_REDIS_INTEGRATION=1 to run Redis integration tests",
)


@pytest.fixture
def memory():
    client = redis.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )

    try:
        client.ping()
    except redis.RedisError:
        pytest.skip("Redis server is unavailable")

    service = RedisChatMemory(
        client=client,
        ttl_seconds=5,
        max_messages=2,
    )

    conversation_ids = [uuid4(), uuid4()]

    yield service, conversation_ids

    for conversation_id in conversation_ids:
        client.delete(service._get_key(conversation_id))

    client.close()


def test_real_redis_stores_and_retrieves_messages(memory):
    service, (conversation_id, _) = memory

    service.add_message(conversation_id, "user", "Hello")
    service.add_message(conversation_id, "assistant", "Hello there")

    history = service.get_history(conversation_id)

    assert history == [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hello there"},
    ]


def test_real_redis_enforces_message_limit(memory):
    service, (conversation_id, _) = memory

    service.add_message(conversation_id, "user", "Message 1")
    service.add_message(conversation_id, "assistant", "Message 2")
    service.add_message(conversation_id, "user", "Message 3")

    history = service.get_history(conversation_id)

    assert len(history) == 2
    assert history[0]["content"] == "Message 2"
    assert history[1]["content"] == "Message 3"


def test_real_redis_isolates_conversations(memory):
    service, (first_id, second_id) = memory

    service.add_message(first_id, "user", "First conversation")
    service.add_message(second_id, "user", "Second conversation")

    assert service.get_history(first_id) == [
        {"role": "user", "content": "First conversation"}
    ]
    assert service.get_history(second_id) == [
        {"role": "user", "content": "Second conversation"}
    ]


def test_real_redis_sets_and_refreshes_ttl(memory):
    service, (conversation_id, _) = memory

    service.add_message(conversation_id, "user", "First message")

    key = service._get_key(conversation_id)
    initial_ttl = service.client.ttl(key)

    assert 0 < initial_ttl <= 5

    time.sleep(2)

    service.add_message(conversation_id, "assistant", "Second message")

    refreshed_ttl = service.client.ttl(key)

    assert refreshed_ttl > 0
    assert refreshed_ttl >= initial_ttl
