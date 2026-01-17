from models import Booker
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, List, Optional
from uuid import UUID, uuid4
from dataclasses import dataclass
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


class InMemoryBookingStore():
    def __init__(self, ALLOWED_ROOMS) -> None:
        self._lock = Lock()
        self._by_room: Dict[str, List[Booking]] = {}
        self._by_id: Dict[UUID, Booking] = {}
        self.ALLOWED_ROOMS = ALLOWED_ROOMS

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
            return {room_id: list(self._by_room.get(room_id, [])) for room_id in self.ALLOWED_ROOMS}