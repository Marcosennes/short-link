"""Event contracts exchanged through Kafka.

Every message shares the same envelope (id, type, timestamp, schema version) and
carries a type-specific payload. Consumers parse raw bytes with the helpers at the
bottom of this module, so a malformed message fails loudly in one place.
"""

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, TypeAdapter

LINK_EVENTS_TOPIC = "link.events"
LINK_CLICKS_TOPIC = "link.clicks"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class _Envelope(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: UUID = Field(default_factory=uuid4)
    occurred_at: datetime = Field(default_factory=_utcnow)
    version: int = 1


# ---------- link.events (published by link-service through the outbox) ----------


class LinkCreatedPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str
    url: AnyHttpUrl
    expires_at: datetime | None = None


class LinkDeletedPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str


class LinkCreatedEvent(_Envelope):
    event_type: Literal["link.created"] = "link.created"
    payload: LinkCreatedPayload


class LinkDeletedEvent(_Envelope):
    event_type: Literal["link.deleted"] = "link.deleted"
    payload: LinkDeletedPayload


LinkEvent = Annotated[LinkCreatedEvent | LinkDeletedEvent, Field(discriminator="event_type")]

# ---------- link.clicks (published by redirect-service) ----------


class LinkClickedPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str
    user_agent: str | None = None
    ip_masked: str | None = None
    referer: str | None = None


class LinkClickedEvent(_Envelope):
    event_type: Literal["link.clicked"] = "link.clicked"
    payload: LinkClickedPayload


# ---------- (de)serialization ----------

_link_event_adapter: TypeAdapter[LinkEvent] = TypeAdapter(LinkEvent)


def serialize(event: _Envelope) -> bytes:
    return event.model_dump_json().encode()


def parse_link_event(raw: bytes | str) -> LinkCreatedEvent | LinkDeletedEvent:
    return _link_event_adapter.validate_json(raw)


def parse_click_event(raw: bytes | str) -> LinkClickedEvent:
    return LinkClickedEvent.model_validate_json(raw)
