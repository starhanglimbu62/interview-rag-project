import logging
from functools import lru_cache

import httpx
import redis
from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.routes.chat import get_llm_service
from app.schemas.booking_conversation import (
    BookingConversationRequest,
    BookingConversationResponse,
)
from app.services.booking_conversation_service import (
    BookingConversationService,
)
from app.services.booking_extraction_service import BookingExtractionService
from app.services.booking_service import BookingService
from app.services.booking_state import RedisBookingState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@lru_cache(maxsize=1)
def get_booking_state() -> RedisBookingState:
    return RedisBookingState()


def get_booking_extraction_service(
    llm_service=Depends(get_llm_service),
) -> BookingExtractionService:
    return BookingExtractionService(llm_service)


def get_booking_service(
    db: Session = Depends(get_db),
) -> BookingService:
    return BookingService(db)


def get_booking_conversation_service(
    extraction_service: BookingExtractionService = Depends(
        get_booking_extraction_service
    ),
    state_store: RedisBookingState = Depends(get_booking_state),
    booking_service: BookingService = Depends(get_booking_service),
) -> BookingConversationService:
    return BookingConversationService(
        extraction_service=extraction_service,
        state_store=state_store,
        booking_service=booking_service,
    )


@router.post(
    "/conversation",
    response_model=BookingConversationResponse,
)
async def booking_conversation(
    request: BookingConversationRequest,
    conversation_service: BookingConversationService = Depends(
        get_booking_conversation_service
    ),
) -> BookingConversationResponse:
    """Collect booking details and confirm interview appointments."""

    try:
        return await run_in_threadpool(
            conversation_service.process,
            request,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except (
        httpx.HTTPError,
        redis.RedisError,
        SQLAlchemyError,
    ) as exc:
        logger.exception(
            "A required service failed during booking conversation"
        )
        raise HTTPException(
            status_code=503,
            detail="A required service is temporarily unavailable",
        ) from exc

    except Exception as exc:
        logger.exception(
            "Unexpected error while processing booking conversation"
        )
        raise HTTPException(
            status_code=500,
            detail="Unable to process booking request",
        ) from exc
