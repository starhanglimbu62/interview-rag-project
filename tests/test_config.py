import pytest

from app.config import _validated_http_url


def test_qdrant_url_defaults_to_local_development_service(monkeypatch):
    monkeypatch.delenv("QDRANT_URL", raising=False)

    assert _validated_http_url(
        "QDRANT_URL",
        "http://localhost:6333",
    ) == "http://localhost:6333"


def test_qdrant_url_supports_compose_service_hostname(monkeypatch):
    monkeypatch.setenv("QDRANT_URL", "http://qdrant:6333/")

    assert _validated_http_url(
        "QDRANT_URL",
        "http://localhost:6333",
    ) == "http://qdrant:6333"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "localhost:6333",
        "ftp://qdrant:6333",
        "http://",
    ],
)
def test_qdrant_url_rejects_invalid_values(monkeypatch, value):
    monkeypatch.setenv("QDRANT_URL", value)

    with pytest.raises(ValueError, match="QDRANT_URL"):
        _validated_http_url(
            "QDRANT_URL",
            "http://localhost:6333",
        )
