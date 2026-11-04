import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import health_service


def test_liveness_endpoint_confirms_process_is_running():
    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_legacy_health_endpoint_remains_compatible():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_readiness_returns_ok_when_all_dependencies_pass(monkeypatch):
    for name in health_service._CHECKS:
        monkeypatch.setitem(health_service._CHECKS, name, lambda: None)

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "dependencies": {
            "postgres": "ok",
            "redis": "ok",
            "qdrant": "ok",
            "ollama": "ok",
        },
    }


def test_readiness_returns_503_without_internal_error_details(monkeypatch):
    def fail_check():
        raise RuntimeError("secret connection details")

    monkeypatch.setitem(
        health_service._CHECKS,
        "postgres",
        fail_check,
    )
    for name in ("redis", "qdrant", "ollama"):
        monkeypatch.setitem(
            health_service._CHECKS,
            name,
            lambda: None,
        )

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "dependencies": {
            "postgres": "unavailable",
            "redis": "ok",
            "qdrant": "ok",
            "ollama": "ok",
        },
    }
    assert "secret connection details" not in response.text


def test_readiness_marks_timed_out_dependency_unavailable(monkeypatch):
    async def timeout(coro, timeout):
        coro.close()
        raise asyncio.TimeoutError

    monkeypatch.setattr(health_service.asyncio, "wait_for", timeout)

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert all(
        status == "unavailable"
        for status in response.json()["dependencies"].values()
    )
