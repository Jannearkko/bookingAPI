# PHASE 1

**Initial prompt:**
```
I have a task to create a simple booking API for meeting rooms. The phase 1 is all about AI and how I can guide you to create your version of that API. 

For this task, I've chosen Python as the language and FastAPI library for connectivity. 

There should be the following services:
- Booking a certain meeting room for specific time span 
- Delete a booking 
- List all reservations of each room 

Business logic: 
- Bookings can't overlap 
- You can't book a room in the past 
- The start time of booking must be before the end time. 

Memory: 
- In-memory database

So get to it please.
```
**Answer:**
```
Below is a clean “phase 1” FastAPI implementation with an in-memory database and the exact business rules you listed.

Project structure:
    meeting-room-booking/
        main.py
        requirements.txt

requirements.txt:
    fastapi
    uvicorn[standard]

main.py:
    from __future__ import annotations
    from dataclasses import dataclass
    from datetime import datetime, timezone
    from threading import Lock
    from typing import Dict, List, Optional
    from uuid import UUID, uuid4
    from fastapi import FastAPI, HTTPException, Path, status
    from pydantic import BaseModel, Field


    # ----------------------------
    # Models (API)
    # ----------------------------

    class BookingCreateRequest(BaseModel):
        start: datetime = Field(..., description="Start time (ISO 8601). Prefer timezone-aware, e.g. 2026-01-17T10:00:00Z")
        end: datetime = Field(..., description="End time (ISO 8601). Prefer timezone-aware, e.g. 2026-01-17T11:00:00Z")
        title: Optional[str] = Field(None, max_length=200)


    class BookingResponse(BaseModel):
        id: UUID
        room_id: str
        start: datetime
        end: datetime
        title: Optional[str] = None
        created_at: datetime


    # ----------------------------
    # In-memory "database"
    # ----------------------------

    @dataclass(frozen=True)
    class Booking:
        id: UUID
        room_id: str
        start: datetime
        end: datetime
        title: Optional[str]
        created_at: datetime


    class InMemoryBookingStore:
        """
        Stores bookings per room.
        Thread-safe with a simple Lock.
        """
        def __init__(self) -> None:
            self._lock = Lock()
            self._by_room: Dict[str, List[Booking]] = {}
            self._by_id: Dict[UUID, Booking] = {}

        @staticmethod
        def _to_utc(dt: datetime) -> datetime:
            # If client sends naive datetimes, treat them as UTC (simple & predictable).
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)

        @staticmethod
        def _now_utc() -> datetime:
            return datetime.now(timezone.utc)

        @staticmethod
        def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
            # Treat as half-open intervals [start, end): end == other.start is allowed
            return a_start < b_end and a_end > b_start

        def create_booking(self, room_id: str, start: datetime, end: datetime, title: Optional[str]) -> Booking:
            start_utc = self._to_utc(start)
            end_utc = self._to_utc(end)
            now = self._now_utc()

            # Business rules
            if start_utc >= end_utc:
                raise ValueError("start_must_be_before_end")
            if start_utc < now:
                raise ValueError("cannot_book_in_the_past")

            with self._lock:
                existing = self._by_room.get(room_id, [])

                # Overlap check
                for b in existing:
                    if self._overlaps(start_utc, end_utc, b.start, b.end):
                        raise RuntimeError("booking_overlaps")

                booking = Booking(
                    id=uuid4(),
                    room_id=room_id,
                    start=start_utc,
                    end=end_utc,
                    title=title,
                    created_at=now,
                )

                # Insert and keep room list sorted by start time (nice for listing)
                updated = existing + [booking]
                updated.sort(key=lambda x: x.start)
                self._by_room[room_id] = updated
                self._by_id[booking.id] = booking

                return booking

        def delete_booking(self, booking_id: UUID) -> None:
            with self._lock:
                booking = self._by_id.get(booking_id)
                if booking is None:
                    raise KeyError("not_found")

                room_list = self._by_room.get(booking.room_id, [])
                room_list = [b for b in room_list if b.id != booking_id]
                self._by_room[booking.room_id] = room_list
                del self._by_id[booking_id]

        def list_bookings_for_room(self, room_id: str) -> List[Booking]:
            with self._lock:
                return list(self._by_room.get(room_id, []))

        def list_all_rooms(self) -> Dict[str, List[Booking]]:
            with self._lock:
                return {room_id: list(bookings) for room_id, bookings in self._by_room.items()}


    store = InMemoryBookingStore()
    app = FastAPI(title="Meeting Room Booking API (Phase 1)", version="1.0.0")


    # ----------------------------
    # Endpoints
    # ----------------------------

    @app.post(
        "/rooms/{room_id}/bookings",
        response_model=BookingResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_booking(
        room_id: str = Path(..., min_length=1, max_length=100),
        payload: BookingCreateRequest = ...,
    ):
        try:
            booking = store.create_booking(
                room_id=room_id,
                start=payload.start,
                end=payload.end,
                title=payload.title,
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


    @app.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_booking(booking_id: UUID):
        try:
            store.delete_booking(booking_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Booking not found.")
        return None


    @app.get("/rooms/{room_id}/bookings", response_model=list[BookingResponse])
    def list_room_bookings(room_id: str = Path(..., min_length=1, max_length=100)):
        bookings = store.list_bookings_for_room(room_id)
        return [BookingResponse(**b.__dict__) for b in bookings]


    @app.get("/rooms/bookings", response_model=dict[str, list[BookingResponse]])
    def list_all_rooms_bookings():
        all_rooms = store.list_all_rooms()
        return {room_id: [BookingResponse(**b.__dict__) for b in bookings] for room_id, bookings in all_rooms.items()}

Run it:
    pip install -r requirements.txt
    uvicorn main:app --reload
```
**2nd prompt:**
```
Very good, all the major services and business logic is working. 

Next, I don't think 100 different meeting rooms is feasible so let's drop that to 5 and give the swagger /docs testing endpoint a more detailed explanation of the options and rules for the user when testing.
```
**Answer:**
```
Cool — let’s hard-limit rooms to 5 and make the Swagger docs much more “tester friendly” with clear rules + allowed room IDs.

Below is a drop-in update to your main.py (replace your file with this, or copy the changed parts).

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Path, status
from pydantic import BaseModel, Field


# ----------------------------
# Room configuration (Phase 1)
# ----------------------------
# Hard limit to 5 meeting rooms.
ALLOWED_ROOMS = ["alpha", "bravo", "charlie", "delta", "echo"]


def _validate_room(room_id: str) -> None:
    if room_id not in ALLOWED_ROOMS:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Room not found.",
                "allowed_rooms": ALLOWED_ROOMS,
            },
        )


# ----------------------------
# Models (API)
# ----------------------------

class BookingCreateRequest(BaseModel):
    start: datetime = Field(
        ...,
        description=(
            "Start time of the booking (ISO 8601).\n\n"
            "**Recommended:** timezone-aware values (e.g. `2026-01-17T10:00:00Z`).\n"
            "If you send a timezone-naive datetime (no `Z` or offset), it will be treated as **UTC**."
        ),
        examples=["2026-01-17T10:00:00Z"],
    )
    end: datetime = Field(
        ...,
        description=(
            "End time of the booking (ISO 8601).\n\n"
            "**Important:** end must be after start. Adjacent bookings are allowed:\n"
            "`10:00–11:00` and `11:00–12:00` do **not** overlap."
        ),
        examples=["2026-01-17T11:00:00Z"],
    )
    title: Optional[str] = Field(
        None,
        max_length=200,
        description="Optional short description for the booking (max 200 chars).",
        examples=["Sprint planning"],
    )


class BookingResponse(BaseModel):
    id: UUID
    room_id: str
    start: datetime
    end: datetime
    title: Optional[str] = None
    created_at: datetime


# ----------------------------
# In-memory "database"
# ----------------------------

@dataclass(frozen=True)
class Booking:
    id: UUID
    room_id: str
    start: datetime
    end: datetime
    title: Optional[str]
    created_at: datetime


class InMemoryBookingStore:
    """
    Stores bookings per room.
    Thread-safe with a simple Lock.

    Business rules enforced on create:
      - start < end
      - start cannot be in the past
      - bookings cannot overlap per room (half-open intervals [start, end))
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._by_room: Dict[str, List[Booking]] = {}
        self._by_id: Dict[UUID, Booking] = {}

    @staticmethod
    def _to_utc(dt: datetime) -> datetime:
        # If client sends naive datetimes, treat them as UTC (simple & predictable).
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @staticmethod
    def _now_utc() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
        # Half-open intervals [start, end): end == other.start is allowed
        return a_start < b_end and a_end > b_start

    def create_booking(self, room_id: str, start: datetime, end: datetime, title: Optional[str]) -> Booking:
        start_utc = self._to_utc(start)
        end_utc = self._to_utc(end)
        now = self._now_utc()

        if start_utc >= end_utc:
            raise ValueError("start_must_be_before_end")
        if start_utc < now:
            raise ValueError("cannot_book_in_the_past")

        with self._lock:
            existing = self._by_room.get(room_id, [])
            for b in existing:
                if self._overlaps(start_utc, end_utc, b.start, b.end):
                    raise RuntimeError("booking_overlaps")

            booking = Booking(
                id=uuid4(),
                room_id=room_id,
                start=start_utc,
                end=end_utc,
                title=title,
                created_at=now,
            )

            updated = existing + [booking]
            updated.sort(key=lambda x: x.start)
            self._by_room[room_id] = updated
            self._by_id[booking.id] = booking
            return booking

    def delete_booking(self, booking_id: UUID) -> None:
        with self._lock:
            booking = self._by_id.get(booking_id)
            if booking is None:
                raise KeyError("not_found")

            room_list = self._by_room.get(booking.room_id, [])
            self._by_room[booking.room_id] = [b for b in room_list if b.id != booking_id]
            del self._by_id[booking_id]

    def list_bookings_for_room(self, room_id: str) -> List[Booking]:
        with self._lock:
            return list(self._by_room.get(room_id, []))

    def list_all_rooms(self) -> Dict[str, List[Booking]]:
        with self._lock:
            # Ensure all 5 rooms are always present in this response (even if empty)
            return {room_id: list(self._by_room.get(room_id, [])) for room_id in ALLOWED_ROOMS}


store = InMemoryBookingStore()

app = FastAPI(
    title="Meeting Room Booking API (Phase 1)",
    version="1.1.0",
    description=(
        "A simple in-memory booking API for **five** meeting rooms.\n\n"
        "## Allowed rooms\n"
        f"- `{ALLOWED_ROOMS[0]}`, `{ALLOWED_ROOMS[1]}`, `{ALLOWED_ROOMS[2]}`, `{ALLOWED_ROOMS[3]}`, `{ALLOWED_ROOMS[4]}`\n\n"
        "## Booking rules\n"
        "- **No overlaps per room**: bookings use half-open intervals **[start, end)**.\n"
        "  - Example: `10:00–11:00` and `11:00–12:00` ✅ allowed (no overlap)\n"
        "  - Example: `10:00–11:00` and `10:30–11:30` ❌ overlap\n"
        "- **No past bookings**: `start` must be >= current time (UTC).\n"
        "- **Valid times**: `start` must be strictly before `end`.\n\n"
        "## Timezones\n"
        "- Prefer timezone-aware timestamps like `2026-01-17T10:00:00Z`.\n"
        "- If you submit a timestamp **without** timezone info, it is treated as **UTC**.\n\n"
        "## Storage\n"
        "- In-memory only: restarting the server clears all bookings."
    ),
)


# ----------------------------
# Endpoints
# ----------------------------

@app.post(
    "/rooms/{room_id}/bookings",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a booking for a room",
    description=(
        "Creates a booking in the given room.\n\n"
        "### Notes for testing\n"
        "- Use one of the **allowed rooms** only.\n"
        "- If your request conflicts with an existing booking, you'll get **409 Conflict**.\n"
        "- If your request violates time rules (past booking, start >= end), you'll get **400 Bad Request**."
    ),
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
    description="Deletes a booking by its UUID. Returns 404 if the booking does not exist.",
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
    description="Returns all bookings for the given room, sorted by start time (UTC).",
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
    description=(
        "Returns a dictionary of **all 5 rooms** mapped to their bookings (possibly empty lists).\n\n"
        "Useful for quickly checking state when testing."
    ),
)
def list_all_rooms_bookings():
    all_rooms = store.list_all_rooms()
    return {room_id: [BookingResponse(**b.__dict__) for b in bookings] for room_id, bookings in all_rooms.items()}


What changed (behavior + docs)

- Room IDs are now restricted to: alpha, bravo, charlie, delta, echo
- Any other room_id returns 404 with allowed_rooms included.
- /docs now explains:
    - allowed rooms
    - overlap behavior ([start, end) so adjacent bookings are OK)
    - no past bookings
    - timezone handling (naive datetimes treated as UTC)
    - in-memory persistence caveat
```
**3rd prompt:**
```
Each endpoint is working as expected, thank you. 

Next, let's add either a "name" or "id" field of the booker to the reservations
```
**Answer:**
```
Got it — we’ll add a required booker object to each reservation, with either id or name required (at least one must be provided). We’ll store it in-memory and return it in responses.

Below are the minimal, clean changes (full file included so you can copy-paste).

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Path, status
from pydantic import BaseModel, Field, model_validator


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


# ----------------------------
# Models (API)
# ----------------------------

class Booker(BaseModel):
    """
    Booker identity. Provide at least one:
      - id: stable identifier (UUID, employee number, etc.)
      - name: display name
    """
    id: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Optional booker identifier (e.g., employee id, UUID-as-string).",
        examples=["emp-12345"],
    )
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=120,
        description="Optional booker display name.",
        examples=["Janne Arkko"],
    )

    @model_validator(mode="after")
    def require_id_or_name(self) -> "Booker":
        if not (self.id or self.name):
            raise ValueError("Either 'id' or 'name' must be provided for the booker.")
        return self


class BookingCreateRequest(BaseModel):
    start: datetime = Field(
        ...,
        description=(
            "Start time of the booking (ISO 8601).\n\n"
            "**Recommended:** timezone-aware values (e.g. `2026-01-17T10:00:00Z`).\n"
            "If you send a timezone-naive datetime (no `Z` or offset), it will be treated as **UTC**."
        ),
        examples=["2026-01-17T10:00:00Z"],
    )
    end: datetime = Field(
        ...,
        description=(
            "End time of the booking (ISO 8601).\n\n"
            "**Important:** end must be after start. Adjacent bookings are allowed:\n"
            "`10:00–11:00` and `11:00–12:00` do **not** overlap."
        ),
        examples=["2026-01-17T11:00:00Z"],
    )
    title: Optional[str] = Field(
        None,
        max_length=200,
        description="Optional short description for the booking (max 200 chars).",
        examples=["Sprint planning"],
    )
    booker: Booker = Field(
        ...,
        description=(
            "Who is booking the room. Must contain at least one of: `id` or `name`.\n\n"
            "Examples:\n"
            '- `{ "id": "emp-12345" }`\n'
            '- `{ "name": "Janne Arkko" }`\n'
            '- `{ "id": "emp-12345", "name": "Janne Arkko" }`'
        ),
        examples=[{"id": "emp-12345", "name": "Janne Arkko"}],
    )


class BookingResponse(BaseModel):
    id: UUID
    room_id: str
    start: datetime
    end: datetime
    title: Optional[str] = None
    booker: Booker
    created_at: datetime


# ----------------------------
# In-memory "database"
# ----------------------------

@dataclass(frozen=True)
class Booking:
    id: UUID
    room_id: str
    start: datetime
    end: datetime
    title: Optional[str]
    booker: Booker
    created_at: datetime


class InMemoryBookingStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._by_room: Dict[str, List[Booking]] = {}
        self._by_id: Dict[UUID, Booking] = {}

    @staticmethod
    def _to_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @staticmethod
    def _now_utc() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
        return a_start < b_end and a_end > b_start

    def create_booking(self, room_id: str, start: datetime, end: datetime, title: Optional[str], booker: Booker) -> Booking:
        start_utc = self._to_utc(start)
        end_utc = self._to_utc(end)
        now = self._now_utc()

        if start_utc >= end_utc:
            raise ValueError("start_must_be_before_end")
        if start_utc < now:
            raise ValueError("cannot_book_in_the_past")

        with self._lock:
            existing = self._by_room.get(room_id, [])
            for b in existing:
                if self._overlaps(start_utc, end_utc, b.start, b.end):
                    raise RuntimeError("booking_overlaps")

            booking = Booking(
                id=uuid4(),
                room_id=room_id,
                start=start_utc,
                end=end_utc,
                title=title,
                booker=booker,
                created_at=now,
            )

            updated = existing + [booking]
            updated.sort(key=lambda x: x.start)
            self._by_room[room_id] = updated
            self._by_id[booking.id] = booking
            return booking

    def delete_booking(self, booking_id: UUID) -> None:
        with self._lock:
            booking = self._by_id.get(booking_id)
            if booking is None:
                raise KeyError("not_found")

            room_list = self._by_room.get(booking.room_id, [])
            self._by_room[booking.room_id] = [b for b in room_list if b.id != booking_id]
            del self._by_id[booking_id]

    def list_bookings_for_room(self, room_id: str) -> List[Booking]:
        with self._lock:
            return list(self._by_room.get(room_id, []))

    def list_all_rooms(self) -> Dict[str, List[Booking]]:
        with self._lock:
            return {room_id: list(self._by_room.get(room_id, [])) for room_id in ALLOWED_ROOMS}


store = InMemoryBookingStore()

app = FastAPI(
    title="Meeting Room Booking API (Phase 1)",
    version="1.2.0",
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
```
**4th prompt:**
```
Thank you, the API is working as expected and each endpoint produces the result required. 

Next, let's implement a simple test script to run through the endpoints to test uniform exception handling and status codes.
```
**Answer:**
```
Below is a simple but thorough test script that runs through all endpoints and checks status codes + error bodies for uniform handling.

It uses pytest + FastAPI TestClient, so it runs fast and doesn’t require Uvicorn to be running.

1) Add test dependencies

Update requirements.txt:
    fastapi
    uvicorn[standard]
    pytest
    httpx

2) Create test_api.py

Put this next to main.py:

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from main import app, ALLOWED_ROOMS

client = TestClient(app)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def future_window(minutes_from_now: int = 10, duration_minutes: int = 60) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    start = now + timedelta(minutes=minutes_from_now)
    end = start + timedelta(minutes=duration_minutes)
    return iso(start), iso(end)


def past_window(minutes_ago: int = 10, duration_minutes: int = 60) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=minutes_ago)
    end = start + timedelta(minutes=duration_minutes)
    return iso(start), iso(end)


def assert_error_shape(resp, expected_status: int):
    """
    Ensures "uniform" error handling:
      - correct status code
      - JSON body has a 'detail'
    """
    assert resp.status_code == expected_status, resp.text
    data = resp.json()
    assert "detail" in data, data


def create_booking(room_id: str, start: str, end: str, booker: dict, title: str | None = None):
    payload = {"start": start, "end": end, "booker": booker}
    if title is not None:
        payload["title"] = title
    return client.post(f"/rooms/{room_id}/bookings", json=payload)


def test_404_unknown_room_on_create():
    start, end = future_window()
    resp = create_booking(
        room_id="not-a-real-room",
        start=start,
        end=end,
        booker={"name": "Tester"},
        title="Should fail",
    )
    # Your API returns 404 with a structured detail object for unknown room
    assert resp.status_code == 404, resp.text
    data = resp.json()
    assert "detail" in data
    assert isinstance(data["detail"], dict)
    assert "allowed_rooms" in data["detail"]
    assert data["detail"]["allowed_rooms"] == ALLOWED_ROOMS


def test_400_start_must_be_before_end():
    now = datetime.now(timezone.utc) + timedelta(minutes=10)
    start = iso(now)
    end = iso(now)  # equal to start -> invalid
    resp = create_booking(
        room_id=ALLOWED_ROOMS[0],
        start=start,
        end=end,
        booker={"id": "emp-1"},
    )
    assert_error_shape(resp, 400)
    assert resp.json()["detail"].lower().find("start") != -1


def test_400_cannot_book_in_the_past():
    start, end = past_window()
    resp = create_booking(
        room_id=ALLOWED_ROOMS[0],
        start=start,
        end=end,
        booker={"name": "Tester"},
    )
    assert_error_shape(resp, 400)
    assert "past" in resp.json()["detail"].lower()


def test_422_booker_missing_id_and_name():
    start, end = future_window()
    resp = create_booking(
        room_id=ALLOWED_ROOMS[0],
        start=start,
        end=end,
        booker={},  # violates validator
    )
    # Pydantic validation errors are 422 by FastAPI
    assert_error_shape(resp, 422)


def test_201_create_and_200_list_room_bookings():
    start, end = future_window(minutes_from_now=15, duration_minutes=30)
    resp = create_booking(
        room_id=ALLOWED_ROOMS[1],
        start=start,
        end=end,
        booker={"id": "emp-123", "name": "Tester"},
        title="Happy path",
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "id" in body
    booking_id = body["id"]
    UUID(booking_id)  # validates format

    list_resp = client.get(f"/rooms/{ALLOWED_ROOMS[1]}/bookings")
    assert list_resp.status_code == 200, list_resp.text
    bookings = list_resp.json()
    assert isinstance(bookings, list)
    assert any(b["id"] == booking_id for b in bookings)


def test_409_overlap_same_room():
    room = ALLOWED_ROOMS[2]
    start1, end1 = future_window(minutes_from_now=20, duration_minutes=60)

    r1 = create_booking(room, start1, end1, booker={"name": "OverlapTester"}, title="Base")
    assert r1.status_code == 201, r1.text

    # Overlap: start inside existing booking window
    # e.g. existing 20..80 minutes, this one 50..110
    now = datetime.now(timezone.utc)
    start2 = iso(now + timedelta(minutes=50))
    end2 = iso(now + timedelta(minutes=110))

    r2 = create_booking(room, start2, end2, booker={"name": "OverlapTester2"}, title="Should conflict")
    assert_error_shape(r2, 409)
    assert "overlap" in r2.json()["detail"].lower()


def test_adjacent_bookings_allowed_no_overlap():
    room = ALLOWED_ROOMS[3]
    now = datetime.now(timezone.utc) + timedelta(minutes=30)

    start_a = iso(now)
    end_a = iso(now + timedelta(minutes=30))
    start_b = end_a  # adjacent
    end_b = iso(now + timedelta(minutes=60))

    r1 = create_booking(room, start_a, end_a, booker={"id": "emp-a"})
    assert r1.status_code == 201, r1.text

    r2 = create_booking(room, start_b, end_b, booker={"id": "emp-b"})
    assert r2.status_code == 201, r2.text


def test_delete_204_then_404_on_second_delete():
    room = ALLOWED_ROOMS[4]
    start, end = future_window(minutes_from_now=25, duration_minutes=15)
    r = create_booking(room, start, end, booker={"name": "Deleter"})
    assert r.status_code == 201, r.text
    booking_id = r.json()["id"]

    d1 = client.delete(f"/bookings/{booking_id}")
    assert d1.status_code == 204, d1.text
    assert d1.text == ""  # No Content

    d2 = client.delete(f"/bookings/{booking_id}")
    assert_error_shape(d2, 404)


def test_list_all_rooms_includes_all_5_keys():
    resp = client.get("/rooms/bookings")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, dict)
    for room in ALLOWED_ROOMS:
        assert room in data
        assert isinstance(data[room], list)

3) Run the tests

pytest -q

What this covers
    - 400: start >= end, past booking
    - 404: unknown room, deleting unknown booking
    - 409: overlap conflict
    - 422: validation errors (missing booker id/name)
    - 201/200/204: success flows
    - Confirms your “detail” error field exists everywhere it should (uniform exception shape)

If you want the tests to enforce even stricter uniformity (e.g., always {"detail": {"code": "...", "message": "..."}}), say the word and I’ll refactor the API to use a single error schema + consistent codes, and adjust these tests accordingly.
```
**5th prompt:**
```
All 9 tests passed. 

This marks the end of phase 1, thank you very much.
```
**Answer:**
```
You’re very welcome — and well done on completing Phase 1. 👏
You guided the scope clearly, validated behavior properly, and ended with automated tests, which is exactly how a solid API phase should close.
```