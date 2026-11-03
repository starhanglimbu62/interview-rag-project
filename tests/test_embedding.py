import pytest

from app.services.embedding_service import (
    EmbeddingService,
    VECTOR_SIZE
)


class FakeModel:
    def get_embedding_dimension(self):
        return VECTOR_SIZE

    def encode(self, texts, **kwargs):
        return [
            [0.1] * VECTOR_SIZE
            for _ in texts
        ]


def test_embed_multiple_texts():
    service = EmbeddingService(model=FakeModel())

    vectors = service.embed_texts([
        "First document chunk",
        "Second document chunk"
    ])

    assert len(vectors) == 2
    assert all(len(vector) == VECTOR_SIZE for vector in vectors)


def test_embed_single_text():
    service = EmbeddingService(model=FakeModel())

    vector = service.embed_text("Interview preparation")

    assert len(vector) == VECTOR_SIZE


def test_empty_list_returns_empty_list():
    service = EmbeddingService(model=FakeModel())

    assert service.embed_texts([]) == []


def test_reject_empty_text():
    service = EmbeddingService(model=FakeModel())

    with pytest.raises(ValueError):
        service.embed_texts(["Valid text", "   "])


def test_reject_wrong_model_dimension():
    class WrongDimensionModel(FakeModel):
        def get_embedding_dimension(self):
            return 128

    with pytest.raises(ValueError):
        EmbeddingService(model=WrongDimensionModel())
