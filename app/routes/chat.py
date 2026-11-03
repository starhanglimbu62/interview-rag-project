import logging
from functools import lru_cache
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from qdrant_client.http.exceptions import UnexpectedResponse

from app.routes import documents as document_routes
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


@lru_cache(maxsize=1)
def get_llm_service() -> LLMService:
    """Create and reuse the Ollama client."""
    return LLMService()


def get_rag_service(
    embedding_service=Depends(document_routes.get_embedding_service),
    vector_store=Depends(document_routes.get_vector_store),
    llm_service=Depends(get_llm_service)
) -> RAGService:
    """Build the RAG service using shared application dependencies."""
    return RAGService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        llm_service=llm_service
    )


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    rag_service: RAGService = Depends(get_rag_service)
) -> ChatResponse:
    """Answer a question using uploaded document context."""

    document_id = (
        str(request.document_id)
        if request.document_id is not None
        else None
    )

    try:
        result = await run_in_threadpool(
            rag_service.answer,
            request.question,
            document_id
        )

        return ChatResponse.model_validate(result)

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc)
        ) from exc

    except (httpx.HTTPError, UnexpectedResponse) as exc:
        logger.exception("An upstream service failed during chat")

        raise HTTPException(
            status_code=503,
            detail="A required service is temporarily unavailable"
        ) from exc

    except Exception as exc:
        logger.exception("Unexpected error while processing chat request")

        raise HTTPException(
            status_code=500,
            detail="Unable to process chat request"
        ) from exc
