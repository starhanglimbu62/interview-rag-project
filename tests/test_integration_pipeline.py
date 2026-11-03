from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_fixed_size_ingestion():

    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "sample.txt",
                b"This is a sample document for testing ingestion."
                * 30,
                "text/plain"
            )
        },
        data={
            "chunking_strategy": "fixed_size",
            "chunk_size": "100",
            "overlap": "20"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "success"
    assert data["chunking"]["strategy"] == "fixed_size"
    assert data["chunking"]["chunk_count"] > 1

    assert (
        data["embedding"]["embedded_chunk_count"]
        == data["chunking"]["chunk_count"]
    )


def test_recursive_ingestion():

    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "sample.txt",
                b"First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
                * 20,
                "text/plain"
            )
        },
        data={
            "chunking_strategy": "recursive",
            "chunk_size": "100",
            "overlap": "20"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["chunking"]["strategy"] == "recursive"
    assert data["chunking"]["chunk_count"] > 1


def test_invalid_chunking_strategy():

    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "sample.txt",
                b"Sample document",
                "text/plain"
            )
        },
        data={
            "chunking_strategy": "invalid"
        }
    )

    assert response.status_code == 400


def test_invalid_overlap():

    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "sample.txt",
                b"Sample document",
                "text/plain"
            )
        },
        data={
            "chunking_strategy": "fixed_size",
            "chunk_size": "100",
            "overlap": "100"
        }
    )

    assert response.status_code == 400


def test_embedding_vectors_not_returned():

    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "sample.txt",
                b"Sample document for embedding testing.",
                "text/plain"
            )
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert "vectors" not in data["embedding"]
    assert "embeddings" not in data