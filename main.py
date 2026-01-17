from __future__ import annotations
from uuid import UUID
from fastapi import FastAPI, HTTPException, Path, status
from models import BookingCreateRequest, BookingResponse
from InMemoryDatabase import InMemoryBookingStore

# ----------------------------
# Room configuration (Phase 1)
# ----------------------------
ALLOWED_ROOMS = ["alpha", "bravo", "charlie", "delta", "echo"]

def _validate_room(room_id: str) -> None:
    if room_id not in ALLOWED_ROOMS:
        raise HTTPException(
            status_code=404,
            detail={"message": "Room not found.", "allowed_rooms": ALLOWED_ROOMS},
        )

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
    _validate_room(room_id)

    try:
        booking = store.create_booking(
            room_id=room_id,
            start=payload.start,
            end=payload.end,
            title=payload.title,
            booker=payload.booker,
        )
    except ValueError as e:
        if str(e) == "start_must_be_before_end":
            raise HTTPException(status_code=400, detail="Start time must be before end time.")
        if str(e) == "cannot_book_in_the_past":
            raise HTTPException(status_code=400, detail="You can't book a room in the past.")
        raise HTTPException(status_code=400, detail="Invalid booking request.")
    except RuntimeError as e:
        if str(e) == "booking_overlaps":
            raise HTTPException(status_code=409, detail="Booking overlaps with an existing booking.")
        raise HTTPException(status_code=409, detail="Booking conflict.")

    return BookingResponse(**booking.__dict__)


@app.delete(
    "/bookings/{booking_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a booking by ID",
)
def delete_booking(booking_id: UUID):
    try:
        store.delete_booking(booking_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Booking not found.")
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
