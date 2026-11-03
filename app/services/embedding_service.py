from math import isfinite
from typing import Any


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
VECTOR_SIZE = 384


class EmbeddingService:
    def __init__(self, model: Any = None) -> None:
        if model is None:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(MODEL_NAME)

        self.model = model

        dimension = self.model.get_embedding_dimension()

        if dimension != VECTOR_SIZE:
            raise ValueError(
                f"Expected {VECTOR_SIZE}-dimensional model, "
                f"got {dimension}"
            )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        if any(not text.strip() for text in texts):
            raise ValueError("Text input cannot contain empty strings")

        vectors = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        if hasattr(vectors, "tolist"):
            vectors = vectors.tolist()

        if len(vectors) != len(texts):
            raise RuntimeError(
                "Embedding count does not match input text count"
            )

        result: list[list[float]] = []

        for vector in vectors:
            values = [float(value) for value in vector]

            if len(values) != VECTOR_SIZE:
                raise RuntimeError(
                    f"Expected vector size {VECTOR_SIZE}, "
                    f"got {len(values)}"
                )

            if not all(isfinite(value) for value in values):
                raise RuntimeError("Embedding contains invalid values")

            result.append(values)

        return result

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]
