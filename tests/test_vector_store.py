import pytest
from unittest.mock import patch

from qdrant_client import QdrantClient

from app.services.vector_store import (
    QdrantVectorStore,
    COLLECTION_NAME,
    VECTOR_SIZE
)


@pytest.fixture
def vector_store():
    client = QdrantClient(":memory:")

    store = QdrantVectorStore(client=client)
    store.create_collection()

    yield store

    client.close()


def test_create_collection(vector_store):
    assert vector_store.client.collection_exists(
        COLLECTION_NAME
    )


def test_uses_configured_qdrant_url():
    with patch("app.services.vector_store.QdrantClient") as client_class:
        with patch(
            "app.services.vector_store.settings.qdrant_url",
            "http://qdrant:6333",
        ):
            QdrantVectorStore()

    client_class.assert_called_once_with(url="http://qdrant:6333")


def test_store_chunks(vector_store):

    chunks = [
        "Python is a programming language.",
        "FastAPI is a Python web framework."
    ]

    embeddings = [
        [0.1] * VECTOR_SIZE,
        [0.2] * VECTOR_SIZE
    ]

    count = vector_store.store_chunks(
        document_id="document-001",
        filename="python.txt",
        chunks=chunks,
        embeddings=embeddings
    )

    assert count == 2


def test_search_chunks(vector_store):

    chunks = [
        "Python is a programming language.",
        "FastAPI is a Python web framework."
    ]

    embeddings = [
        [0.1] * VECTOR_SIZE,
        [0.2] * VECTOR_SIZE
    ]

    vector_store.store_chunks(
        document_id="document-001",
        filename="python.txt",
        chunks=chunks,
        embeddings=embeddings
    )

    results = vector_store.search(
        query_vector=[0.1] * VECTOR_SIZE,
        limit=2
    )

    assert len(results) == 2
    assert "text" in results[0]
    assert "score" in results[0]


def test_search_by_document_id(vector_store):

    vector_store.store_chunks(
        document_id="document-001",
        filename="first.txt",
        chunks=["First document content"],
        embeddings=[[0.1] * VECTOR_SIZE]
    )

    vector_store.store_chunks(
        document_id="document-002",
        filename="second.txt",
        chunks=["Second document content"],
        embeddings=[[0.2] * VECTOR_SIZE]
    )

    results = vector_store.search(
        query_vector=[0.1] * VECTOR_SIZE,
        document_id="document-001"
    )

    assert len(results) == 1
    assert results[0]["document_id"] == "document-001"


def test_reject_mismatched_chunk_and_embedding_count(vector_store):

    with pytest.raises(ValueError):
        vector_store.store_chunks(
            document_id="document-001",
            filename="test.txt",
            chunks=["First chunk", "Second chunk"],
            embeddings=[[0.1] * VECTOR_SIZE]
        )


def test_reject_wrong_vector_dimension(vector_store):

    with pytest.raises(ValueError):
        vector_store.store_chunks(
            document_id="document-001",
            filename="test.txt",
            chunks=["Test chunk"],
            embeddings=[[0.1] * 128]
        )


def test_reject_empty_chunks(vector_store):

    with pytest.raises(ValueError):
        vector_store.store_chunks(
            document_id="document-001",
            filename="test.txt",
            chunks=[],
            embeddings=[]
        )


def test_reject_invalid_search_dimension(vector_store):

    with pytest.raises(ValueError):
        vector_store.search(
            query_vector=[0.1] * 128
        )


def test_reject_invalid_search_limit(vector_store):

    with pytest.raises(ValueError):
        vector_store.search(
            query_vector=[0.1] * VECTOR_SIZE,
            limit=0
        )