from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

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


def create_booking(room_id: str, start: str, end: str, booker: dict, title: str | None = None):
    payload = {"start": start, "end": end, "booker": booker}
    if title is not None:
        payload["title"] = title
    return client.post(f"/rooms/{room_id}/bookings", json=payload)


def assert_api_error(resp, expected_status: int, expected_code: str, message_contains: str | None = None):
    """
    Assert your unified ApiError shape:
      - correct status
      - detail is a dict with code + message
      - optional substring check on message
    """
    assert resp.status_code == expected_status, resp.text
    data = resp.json()
    assert "detail" in data, data
    assert isinstance(data["detail"], dict), data
    detail = data["detail"]

    assert detail.get("code") == expected_code, detail
    assert isinstance(detail.get("message"), str) and detail["message"], detail

    if message_contains is not None:
        assert message_contains.lower() in detail["message"].lower(), detail


def assert_validation_error_422(resp):
    """
    FastAPI/Pydantic validation errors (422) are not your ApiError unless you install
    a custom RequestValidationError handler.
    """
    assert resp.status_code == 422, resp.text
    data = resp.json()
    assert "detail" in data, data
    # Pydantic returns a list of error objects
    assert isinstance(data["detail"], list), data


def test_404_unknown_room_on_create():
    start, end = future_window()
    resp = create_booking(
        room_id="not-a-real-room",
        start=start,
        end=end,
        booker={"name": "Tester"},
        title="Should fail",
    )

    assert_api_error(resp, 404, "ROOM_NOT_FOUND", message_contains="room not found")
    detail = resp.json()["detail"]
    assert detail.get("allowed_rooms") == ALLOWED_ROOMS


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

    assert_api_error(resp, 400, "BOOKING_START_AFTER_END", message_contains="start time")


def test_400_cannot_book_in_the_past():
    start, end = past_window()
    resp = create_booking(
        room_id=ALLOWED_ROOMS[0],
        start=start,
        end=end,
        booker={"name": "Tester"},
    )

    assert_api_error(resp, 400, "BOOKING_IN_PAST", message_contains="past")


def test_422_booker_missing_id_and_name():
    start, end = future_window()
    resp = create_booking(
        room_id=ALLOWED_ROOMS[0],
        start=start,
        end=end,
        booker={},  # violates validator
    )

    assert_validation_error_422(resp)


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
    UUID(booking_id)

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

    now = datetime.now(timezone.utc)
    start2 = iso(now + timedelta(minutes=50))
    end2 = iso(now + timedelta(minutes=110))

    r2 = create_booking(room, start2, end2, booker={"name": "OverlapTester2"}, title="Should conflict")

    assert_api_error(r2, 409, "BOOKING_OVERLAPS", message_contains="overlap")


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
    assert d1.text == ""

    d2 = client.delete(f"/bookings/{booking_id}")
    assert_api_error(d2, 404, "BOOKING_NOT_FOUND", message_contains="not found")


def test_list_all_rooms_includes_all_5_keys():
    resp = client.get("/rooms/bookings")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, dict)
    for room in ALLOWED_ROOMS:
        assert room in data
        assert isinstance(data[room], list)

def test_404_unknown_route_uses_api_error_shape():
    resp = client.get("/this-route-does-not-exist")
    assert_api_error(resp, 404, "ROUTE_NOT_FOUND", message_contains="not found")
