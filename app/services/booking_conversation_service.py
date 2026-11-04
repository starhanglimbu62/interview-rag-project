from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from app.schemas.booking import BookingRequest, BookingResponse
from app.schemas.booking_conversation import (
    BookingConversationRequest,
    BookingConversationResponse,
)
from app.schemas.booking_extraction import BookingExtraction
from app.services.booking_extraction_service import BookingExtractionService
from app.services.booking_service import BookingService, BookingSlotUnavailableError
from app.services.booking_state import RedisBookingState


class BookingConversationService:
    """Orchestrate conversational interview booking."""

    REQUIRED_FIELDS = (
        "candidate_name",
        "email",
        "interview_at",
    )

    def __init__(
        self,
        extraction_service: BookingExtractionService,
        state_store: RedisBookingState,
        booking_service: BookingService,
    ) -> None:
        self.extraction_service = extraction_service
        self.state_store = state_store
        self.booking_service = booking_service

    def process(
        self,
        request: BookingConversationRequest,
    ) -> BookingConversationResponse:
        """Process a booking conversation message."""

        conversation_id = request.conversation_id or uuid4()

        if request.confirm_booking:
            return self._confirm_booking(conversation_id)

        existing_details = self.state_store.get_state(conversation_id)

        updated_details = self.extraction_service.extract(
            request.message,
            existing_details,
        )

        self.state_store.save_state(
            conversation_id,
            updated_details,
        )

        missing_fields = self._get_missing_fields(updated_details)

        if missing_fields:
            return BookingConversationResponse(
                conversation_id=conversation_id,
                message=self._build_missing_details_message(missing_fields),
                status="collecting_details",
                missing_fields=missing_fields,
                booking_details=updated_details,
            )

        try:
            booking_request = BookingRequest.model_validate(
                updated_details.model_dump()
            )
        except ValidationError as exc:
            invalid_fields = self._get_invalid_fields(exc)

            return BookingConversationResponse(
                conversation_id=conversation_id,
                message=self._build_invalid_details_message(invalid_fields),
                status="collecting_details",
                missing_fields=invalid_fields,
                booking_details=updated_details,
            )

        if not self.booking_service.is_slot_available(
            booking_request.interview_at
        ):
            return self._slot_unavailable_response(
                conversation_id,
                updated_details,
            )

        self.state_store.mark_awaiting_confirmation(conversation_id)

        return BookingConversationResponse(
            conversation_id=conversation_id,
            message=self._build_confirmation_message(booking_request),
            status="awaiting_confirmation",
            booking_details=updated_details,
        )

    def _confirm_booking(
        self,
        conversation_id: UUID,
    ) -> BookingConversationResponse:
        """Create a booking only after explicit confirmation."""

        details = self.state_store.get_state(conversation_id)

        if details is None:
            raise ValueError("No booking details exist for this conversation")

        if not self.state_store.is_awaiting_confirmation(conversation_id):
            raise ValueError(
                "Booking details have not been presented for confirmation "
                "or have changed"
            )

        try:
            booking_request = BookingRequest.model_validate(
                details.model_dump()
            )
        except ValidationError as exc:
            invalid_fields = self._get_invalid_fields(exc)

            self.state_store.save_state(conversation_id, details)

            return BookingConversationResponse(
                conversation_id=conversation_id,
                message=self._build_invalid_details_message(invalid_fields),
                status="collecting_details",
                missing_fields=invalid_fields,
                booking_details=details,
            )

        try:
            booking = self.booking_service.create_booking(booking_request)
        except BookingSlotUnavailableError:
            self.state_store.save_state(conversation_id, details)

            return self._slot_unavailable_response(
                conversation_id,
                details,
            )

        self.state_store.clear_state(conversation_id)

        return BookingConversationResponse(
            conversation_id=conversation_id,
            message="Your interview has been booked successfully.",
            status="confirmed",
            booking_details=details,
            booking=BookingResponse.model_validate(booking),
        )

    @classmethod
    def _get_missing_fields(
        cls,
        details: BookingExtraction,
    ) -> list[str]:
        return [
            field
            for field in cls.REQUIRED_FIELDS
            if getattr(details, field) is None
        ]

    @staticmethod
    def _get_invalid_fields(
        exc: ValidationError,
    ) -> list[str]:
        fields = []

        for error in exc.errors():
            field = error["loc"][0]

            if isinstance(field, str) and field not in fields:
                fields.append(field)

        return fields

    @staticmethod
    def _build_missing_details_message(
        missing_fields: list[str],
    ) -> str:
        field_labels = {
            "candidate_name": "your full name",
            "email": "your email address",
            "interview_at": "your preferred interview date and time",
        }

        requested = [
            field_labels[field]
            for field in missing_fields
        ]

        if len(requested) == 1:
            details_text = requested[0]
        else:
            details_text = ", ".join(requested[:-1])
            details_text += f" and {requested[-1]}"

        return f"Please provide {details_text} to continue."

    @staticmethod
    def _build_invalid_details_message(
        invalid_fields: list[str],
    ) -> str:
        messages = {
            "candidate_name": "Please provide a valid full name.",
            "email": "Please provide a valid email address.",
            "interview_at": (
                "Please provide a valid interview date and time "
                "in the future, including the timezone."
            ),
        }

        return " ".join(
            messages[field]
            for field in invalid_fields
            if field in messages
        ) or "Some booking details are invalid. Please correct them."

    @staticmethod
    def _build_confirmation_message(
        request: BookingRequest,
    ) -> str:
        kathmandu_time = request.interview_at.astimezone(
            ZoneInfo("Asia/Kathmandu")
        )

        formatted_time = kathmandu_time.strftime(
            "%A, %d %B %Y at %I:%M %p %Z"
        )

        return (
            "Please review your interview booking:\n"
            f"Name: {request.candidate_name}\n"
            f"Email: {request.email}\n"
            f"Interview: {formatted_time}\n\n"
            "Reply with confirmation to book this interview."
        )

    def _slot_unavailable_response(
        self,
        conversation_id: UUID,
        details: BookingExtraction,
    ) -> BookingConversationResponse:
        return BookingConversationResponse(
            conversation_id=conversation_id,
            message=(
                "That interview time is no longer available. "
                "Please provide another date and time."
            ),
            status="slot_unavailable",
            missing_fields=["interview_at"],
            booking_details=details,
        )

