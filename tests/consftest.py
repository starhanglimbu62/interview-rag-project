import pytest

from app.routes import documents


class FakeEmbeddingService:

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [
            [0.1] * 384
            for _ in texts
        ]


@pytest.fixture(autouse=True)
def mock_embedding_service(monkeypatch):

    monkeypatch.setattr(
        documents,
        "get_embedding_service",
        lambda: FakeEmbeddingService()
    )