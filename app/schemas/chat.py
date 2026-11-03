from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=4000)
    document_id: UUID | None = None
    conversation_id: UUID | None = None

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question cannot be empty")
        return value


class SourceCitation(BaseModel):
    source_id: str
    document_id: str | None
    filename: str
    chunk_index: int | None
    score: float | None = None


class ChatResponse(BaseModel):
    conversation_id: UUID
    answer: str
    sources: list[SourceCitation]
