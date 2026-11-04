import asyncio
import logging
from collections.abc import Callable
from typing import Any

import httpx
import redis
from sqlalchemy import text

from app.config import settings
from app.database import engine

logger = logging.getLogger(__name__)


def check_postgres() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def check_redis() -> None:
    client = redis.Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=settings.health_timeout_seconds,
        socket_timeout=settings.health_timeout_seconds,
    )
    try:
        if not client.ping():
            raise RuntimeError("Redis ping failed")
    finally:
        client.close()


def check_qdrant() -> None:
    with httpx.Client(timeout=settings.health_timeout_seconds) as client:
        response = client.get(f"{settings.qdrant_url}/healthz")
        response.raise_for_status()


def check_ollama() -> None:
    with httpx.Client(
        base_url=settings.ollama_base_url,
        timeout=settings.health_timeout_seconds,
    ) as client:
        response = client.get("/api/tags")
        response.raise_for_status()
        models = response.json().get("models", [])

    if not any(
        isinstance(model, dict)
        and model.get("name") == settings.ollama_model
        for model in models
    ):
        raise RuntimeError("Configured Ollama model is unavailable")


_CHECKS: dict[str, Callable[[], None]] = {
    "postgres": check_postgres,
    "redis": check_redis,
    "qdrant": check_qdrant,
    "ollama": check_ollama,
}


async def check_readiness() -> dict[str, Any]:
    results: dict[str, str] = {}

    async def run_check(
        name: str,
        check: Callable[[], None],
    ) -> None:
        try:
            await asyncio.wait_for(
                asyncio.to_thread(check),
                timeout=settings.health_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning("Readiness check timed out: %s", name)
            results[name] = "unavailable"
        except Exception:
            logger.warning("Readiness check failed: %s", name)
            results[name] = "unavailable"
        else:
            results[name] = "ok"

    await asyncio.gather(
        *(run_check(name, check) for name, check in _CHECKS.items())
    )

    ready = all(status == "ok" for status in results.values())
    return {
        "status": "ready" if ready else "not_ready",
        "dependencies": results,
    }
