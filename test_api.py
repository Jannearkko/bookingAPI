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
