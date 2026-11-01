import json
from uuid import UUID

import pytest
from pydantic import ValidationError

from shortlink_contracts import (
    LinkClickedEvent,
    LinkClickedPayload,
    LinkCreatedEvent,
    LinkCreatedPayload,
    LinkDeletedEvent,
    LinkDeletedPayload,
    parse_click_event,
    parse_link_event,
    serialize,
)


def test_envelope_defaults_are_generated():
    event = LinkDeletedEvent(payload=LinkDeletedPayload(slug="abc"))

    assert isinstance(event.event_id, UUID)
    assert event.occurred_at.tzinfo is not None
    assert event.version == 1
    assert event.event_type == "link.deleted"


def test_link_created_roundtrip():
    event = LinkCreatedEvent(payload=LinkCreatedPayload(slug="abc", url="https://example.com"))

    parsed = parse_link_event(serialize(event))

    assert parsed == event


@pytest.mark.parametrize(
    ("event", "expected_type"),
    [
        (
            LinkCreatedEvent(payload=LinkCreatedPayload(slug="a", url="https://a.io")),
            LinkCreatedEvent,
        ),
        (LinkDeletedEvent(payload=LinkDeletedPayload(slug="a")), LinkDeletedEvent),
    ],
)
def test_parse_link_event_dispatches_on_event_type(event, expected_type):
    assert isinstance(parse_link_event(serialize(event)), expected_type)


def test_parse_link_event_rejects_unknown_type():
    raw = json.dumps({"event_type": "link.renamed", "payload": {"slug": "a"}})

    with pytest.raises(ValidationError):
        parse_link_event(raw)


def test_link_created_rejects_invalid_url():
    with pytest.raises(ValidationError):
        LinkCreatedPayload(slug="a", url="not-a-url")


def test_click_event_roundtrip():
    event = LinkClickedEvent(payload=LinkClickedPayload(slug="abc", user_agent="curl/8.5"))

    assert parse_click_event(serialize(event)) == event
