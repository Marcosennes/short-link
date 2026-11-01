"""Builds outbox messages from the shared event contracts."""

from datetime import datetime

from link_service.domain.models import Link, OutboxMessage
from shortlink_contracts import (
    LINK_EVENTS_TOPIC,
    LinkCreatedEvent,
    LinkCreatedPayload,
    LinkDeletedEvent,
    LinkDeletedPayload,
)


def _to_message(event: LinkCreatedEvent | LinkDeletedEvent, key: str) -> OutboxMessage:
    return OutboxMessage(
        event_id=event.event_id,
        topic=LINK_EVENTS_TOPIC,
        key=key,
        event_type=event.event_type,
        payload=event.model_dump(mode="json"),
        created_at=event.occurred_at,
    )


def link_created(link: Link, occurred_at: datetime) -> OutboxMessage:
    event = LinkCreatedEvent(
        occurred_at=occurred_at,
        payload=LinkCreatedPayload(slug=link.slug, url=link.url, expires_at=link.expires_at),
    )
    return _to_message(event, key=link.slug)


def link_deleted(slug: str, occurred_at: datetime) -> OutboxMessage:
    event = LinkDeletedEvent(occurred_at=occurred_at, payload=LinkDeletedPayload(slug=slug))
    return _to_message(event, key=slug)
