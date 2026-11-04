from math import isfinite
from uuid import NAMESPACE_URL, uuid5
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FilterSelector,
    FieldCondition,
    MatchValue
)

from app.config import settings


COLLECTION_NAME = "document_chunks"
VECTOR_SIZE = 384

class QdrantVectorStore:

    def __init__(self, client: Any = None) -> None:
        self.client = client or QdrantClient(url=settings.qdrant_url)

    def create_collection(self) -> None:
        """
        Create the document collection if it does not exist.
        """

        if self.client.collection_exists(COLLECTION_NAME):
            return

        self.client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE
            )
        )

    def store_chunks(
        self,
        document_id: str,
        filename: str,
        chunks: list[str],
        embeddings: list[list[float]]
    ) -> int:
        """
        Store document chunks and their embeddings in Qdrant.
        """

        if not document_id.strip():
            raise ValueError("Document ID is required")

        if not filename.strip():
            raise ValueError("Filename is required")

        if len(chunks) != len(embeddings):
            raise ValueError(
                "Chunk count and embedding count must match"
            )

        if not chunks:
            raise ValueError("No chunks provided")

        points = []

        for index, (chunk, embedding) in enumerate(
            zip(chunks, embeddings)
        ):

            if not chunk.strip():
                raise ValueError("Chunk text cannot be empty")

            if len(embedding) != VECTOR_SIZE:
                raise ValueError(
                    f"Expected {VECTOR_SIZE}-dimensional vector, "
                    f"got {len(embedding)}"
                )

            vector = [float(value) for value in embedding]

            if not all(isfinite(value) for value in vector):
                raise ValueError("Embedding contains invalid values")

            point_id = str(
                uuid5(
                    NAMESPACE_URL,
                    f"{document_id}:{index}"
                )
            )

            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "document_id": document_id,
                        "filename": filename,
                        "chunk_index": index,
                        "text": chunk
                    }
                )
            )

        self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
            wait=True
        )

        return len(points)

    def search(
        self,
        query_vector: list[float],
        limit: int = 5,
        document_id: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Search for similar document chunks.
        Optionally restrict results to one document.
        """

        if len(query_vector) != VECTOR_SIZE:
            raise ValueError(
                f"Expected {VECTOR_SIZE}-dimensional query vector"
            )

        if not all(isfinite(float(value)) for value in query_vector):
            raise ValueError("Query vector contains invalid values")

        if limit <= 0:
            raise ValueError("Limit must be greater than zero")

        query_filter = None

        if document_id is not None:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id)
                    )
                ]
            )

        response = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=[float(value) for value in query_vector],
            query_filter=query_filter,
            limit=limit,
            with_payload=True
        )

        return [
            {
                "score": point.score,
                "document_id": point.payload["document_id"],
                "filename": point.payload["filename"],
                "chunk_index": point.payload["chunk_index"],
                "text": point.payload["text"]
            }
            for point in response.points
        ]
    def delete_document(self, document_id: str) -> None:
        """
        Delete all chunks belonging to a document.
        """

        self.client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id)
                        )
                    ]
                )
            ),
            wait=True
        )