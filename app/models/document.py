from datetime import datetime

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    func
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    file_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )

    character_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    chunk_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    chunking_strategy: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    chunk_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    overlap: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    embedding_model: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    vector_database: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ready"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
