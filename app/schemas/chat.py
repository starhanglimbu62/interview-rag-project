from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatRequest(BaseModel):
    """Request payload for document-based questions."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=4000)
    document_id: UUID | None = None

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Question cannot be empty")

        return value


class SourceCitation(BaseModel):
    """Metadata identifying a retrieved document chunk."""

    source_id: str
    document_id: str | None
    filename: str
    chunk_index: int | None
    score: float | None = None


class ChatResponse(BaseModel):
    """Response containing the generated answer and its sources."""

    answer: str
    sources: list[SourceCitation]
