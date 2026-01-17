from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import datetime
from uuid import UUID
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
        examples=["Joe Doe"],
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
            '- `{ "name": "Joe Doe" }`\n'
            '- `{ "id": "emp-12345", "name": "Joe Doe" }`'
        ),
        examples=[{"id": "emp-12345", "name": "Joe Doe"}],
    )


class BookingResponse(BaseModel):
    id: UUID
    room_id: str
    start: datetime
    end: datetime
    title: Optional[str] = None
    booker: Booker
    created_at: datetime