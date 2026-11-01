import json
from datetime import UTC, datetime

import pytest

from link_service.domain import events
from link_service.domain.errors import InvalidSlugError
from link_service.domain.models import GENERATED_SLUG_LENGTH, Link, generate_slug, validate_slug
from shortlink_contracts import LinkCreatedEvent, LinkDeletedEvent, parse_link_event

NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.mark.parametrize("slug", ["abc", "my-link", "My_Link_2026", "x" * 32])
def test_validate_slug_accepts_valid_slugs(slug):
    assert validate_slug(slug) == slug


@pytest.mark.parametrize("slug", ["ab", "x" * 33, "has space", "acentuação", "a/b", ""])
def test_validate_slug_rejects_invalid_slugs(slug):
    with pytest.raises(InvalidSlugError):
        validate_slug(slug)


def test_generate_slug_produces_valid_random_slugs():
    slugs = {generate_slug() for _ in range(50)}

    assert len(slugs) == 50
    assert all(len(s) == GENERATED_SLUG_LENGTH and validate_slug(s) for s in slugs)


def test_link_created_message_follows_the_contract():
    link = Link(slug="docs", url="https://example.com/docs", created_at=NOW)

    message = events.link_created(link, occurred_at=NOW)
    event = parse_link_event(json.dumps(message.payload))

    assert isinstance(event, LinkCreatedEvent)
    assert message.topic == "link.events"
    assert message.key == "docs"
    assert message.event_id == event.event_id
    assert str(event.payload.url) == "https://example.com/docs"


def test_link_deleted_message_follows_the_contract():
    message = events.link_deleted("docs", occurred_at=NOW)

    assert message.event_type == "link.deleted"
    assert message.payload["payload"] == {"slug": "docs"}
    assert LinkDeletedEvent.model_validate(message.payload).payload.slug == "docs"
