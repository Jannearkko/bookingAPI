from __future__ import annotations
from uuid import UUID
from fastapi import FastAPI, HTTPException, Path, status
from models import BookingCreateRequest, BookingResponse
from InMemoryDatabase import InMemoryBookingStore
from errors import (
    BOOKING_START_AFTER_END,
    BOOKING_IN_PAST,
    BOOKING_INVALID_REQUEST,
    BOOKING_OVERLAPS,
    BOOKING_CONFLICT,
    BOOKING_NOT_FOUND,
    raise_api_error,
    ROOM_NOT_FOUND
)


# ----------------------------
# Room configuration (Phase 1)
# ----------------------------
ALLOWED_ROOMS = ["alpha", "bravo", "charlie", "delta", "echo"]

def _validate_room(room_id: str) -> None:
    if room_id not in ALLOWED_ROOMS:
        raise_api_error(ROOM_NOT_FOUND, extra={"allowed_rooms": ALLOWED_ROOMS})

# Calling the InMemoryBookingStore-constructor and passing the ALLOWED_ROOMS as parameter
store = InMemoryBookingStore(ALLOWED_ROOMS)

app = FastAPI(
    title="Meeting Room Booking API (Phase 1)",
    version="1.0.0",
    description=(
        "A simple in-memory booking API for **five** meeting rooms.\n\n"
        "## Allowed rooms\n"
        f"- `{ALLOWED_ROOMS[0]}`, `{ALLOWED_ROOMS[1]}`, `{ALLOWED_ROOMS[2]}`, `{ALLOWED_ROOMS[3]}`, `{ALLOWED_ROOMS[4]}`\n\n"
        "## Booking rules\n"
        "- **No overlaps per room**: bookings use half-open intervals **[start, end)**.\n"
        "- **No past bookings**: `start` must be >= current time (UTC).\n"
        "- **Valid times**: `start` must be strictly before `end`.\n"
        "- **Booker required**: provide at least one of `booker.id` or `booker.name`.\n\n"
        "## Timezones\n"
        "- Prefer timezone-aware timestamps like `2026-01-17T10:00:00Z`.\n"
        "- Naive timestamps are treated as **UTC**.\n\n"
        "## Storage\n"
        "- In-memory only: restarting the server clears all bookings."
    ),
)

# POST-endpoint to book a room
@app.post(
    "/rooms/{room_id}/bookings",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a booking for a room",
)
def create_booking(
    room_id: str = Path(
        ...,
        description=f"Meeting room id. Allowed: {', '.join(ALLOWED_ROOMS)}",
        examples=ALLOWED_ROOMS[:2],
    ),
    payload: BookingCreateRequest = ...,
):
    _validate_room(room_id) # Validate "room" exists in ALLOWED_ROOMS

    try:
        booking = store.create_booking(
            room_id=room_id, # str
            start=payload.start, # datetime
            end=payload.end, # datetime
            title=payload.title, # Optional[str]
            booker=payload.booker, # Booker
        )
    except ValueError as e:
        if str(e) == "start_must_be_before_end":
            raise_api_error(BOOKING_START_AFTER_END)
        if str(e) == "cannot_book_in_the_past":
            raise_api_error(BOOKING_IN_PAST)
        raise_api_error(BOOKING_INVALID_REQUEST)

    except RuntimeError as e:
        if str(e) == "booking_overlaps":
            raise_api_error(BOOKING_OVERLAPS)
        raise_api_error(BOOKING_CONFLICT)


@app.delete(
    "/bookings/{booking_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a booking by ID",
)
def delete_booking(booking_id: UUID):
    try:
        store.delete_booking(booking_id)
    except KeyError:
        raise_api_error(BOOKING_NOT_FOUND)
    return None


@app.get(
    "/rooms/{room_id}/bookings",
    response_model=list[BookingResponse],
    summary="List bookings for a room",
)
def list_room_bookings(
    room_id: str = Path(
        ...,
        description=f"Meeting room id. Allowed: {', '.join(ALLOWED_ROOMS)}",
        examples=ALLOWED_ROOMS[:2],
    )
):
    _validate_room(room_id)
    bookings = store.list_bookings_for_room(room_id)
    return [BookingResponse(**b.__dict__) for b in bookings]


@app.get(
    "/rooms/bookings",
    response_model=dict[str, list[BookingResponse]],
    summary="List bookings for all rooms",
)
def list_all_rooms_bookings():
    all_rooms = store.list_all_rooms()
    return {room_id: [BookingResponse(**b.__dict__) for b in bookings] for room_id, bookings in all_rooms.items()}
