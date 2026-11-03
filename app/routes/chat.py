import logging
from functools import lru_cache
from uuid import uuid4

import httpx
import redis
from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from qdrant_client.http.exceptions import UnexpectedResponse

from app.routes import documents as document_routes
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_memory import RedisChatMemory
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@lru_cache(maxsize=1)
def get_llm_service() -> LLMService:
    return LLMService()


@lru_cache(maxsize=1)
def get_chat_memory() -> RedisChatMemory:
    return RedisChatMemory()


def get_rag_service(
    embedding_service=Depends(document_routes.get_embedding_service),
    vector_store=Depends(document_routes.get_vector_store),
    llm_service=Depends(get_llm_service),
) -> RAGService:
    return RAGService(embedding_service, vector_store, llm_service)


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    rag_service: RAGService = Depends(get_rag_service),
    memory: RedisChatMemory = Depends(get_chat_memory),
) -> ChatResponse:
    conversation_id = request.conversation_id or uuid4()
    document_id = (
        str(request.document_id)
        if request.document_id is not None
        else None
    )

    try:
        history = await run_in_threadpool(
            memory.get_history,
            conversation_id,
        )

        result = await run_in_threadpool(
            rag_service.answer,
            request.question,
            document_id,
            history,
        )

        await run_in_threadpool(
            memory.add_message,
            conversation_id,
            "user",
            request.question,
        )

        await run_in_threadpool(
            memory.add_message,
            conversation_id,
            "assistant",
            result["answer"],
        )

        return ChatResponse(
            conversation_id=conversation_id,
            **result,
        )

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    except (
        httpx.HTTPError,
        redis.RedisError,
        UnexpectedResponse,
    ) as exc:
        logger.exception("A required service failed during chat")
        raise HTTPException(
            status_code=503,
            detail="A required service is temporarily unavailable",
        ) from exc

    except Exception as exc:
        logger.exception("Unexpected error while processing chat request")
        raise HTTPException(
            status_code=500,
            detail="Unable to process chat request",
        ) from exc
