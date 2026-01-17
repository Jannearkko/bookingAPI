from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from fastapi import HTTPException, status


@dataclass(frozen=True)
class ApiError:
    code: str
    message: str
    http_status: int

    def to_http_exception(self, *, extra: Optional[Dict[str, Any]] = None) -> HTTPException:
        """
        Convert this error to FastAPI's HTTPException.
        If extra is provided, it will be included in the detail payload.
        """
        detail: Any

        detail = {"code": self.code, "message": self.message}
        if extra:
            detail.update(extra)

        return HTTPException(status_code=self.http_status, detail=detail)


def raise_api_error(err: ApiError, *, extra: Optional[Dict[str, Any]] = None) -> None:
    raise err.to_http_exception(extra=extra)


# ----------------------------
# Room errors
# ----------------------------

ROOM_NOT_FOUND = ApiError(
    code="ROOM_NOT_FOUND",
    message="Room not found.",
    http_status=status.HTTP_404_NOT_FOUND,
)

# ----------------------------
# Booking validation errors (400)
# ----------------------------

BOOKING_START_AFTER_END = ApiError(
    code="BOOKING_START_AFTER_END",
    message="Start time must be before end time.",
    http_status=status.HTTP_400_BAD_REQUEST,
)

BOOKING_IN_PAST = ApiError(
    code="BOOKING_IN_PAST",
    message="You can't book a room in the past.",
    http_status=status.HTTP_400_BAD_REQUEST,
)

BOOKING_INVALID_REQUEST = ApiError(
    code="BOOKING_INVALID_REQUEST",
    message="Invalid booking request.",
    http_status=status.HTTP_400_BAD_REQUEST,
)

# ----------------------------
# Booking conflict errors (409)
# ----------------------------

BOOKING_OVERLAPS = ApiError(
    code="BOOKING_OVERLAPS",
    message="Booking overlaps with an existing booking.",
    http_status=status.HTTP_409_CONFLICT,
)

BOOKING_CONFLICT = ApiError(
    code="BOOKING_CONFLICT",
    message="Booking conflict.",
    http_status=status.HTTP_409_CONFLICT,
)

# ----------------------------
# Booking not found (404)
# ----------------------------

BOOKING_NOT_FOUND = ApiError(
    code="BOOKING_NOT_FOUND",
    message="Booking not found.",
    http_status=status.HTTP_404_NOT_FOUND,
)
