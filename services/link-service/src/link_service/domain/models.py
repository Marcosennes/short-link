import re
import secrets
import string
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from link_service.domain.errors import InvalidSlugError

SLUG_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,32}$")
GENERATED_SLUG_LENGTH = 7
_ALPHABET = string.ascii_letters + string.digits


def validate_slug(slug: str) -> str:
    if not SLUG_PATTERN.fullmatch(slug):
        raise InvalidSlugError(
            "slug must have 3-32 characters: letters, digits, '-' or '_'",
        )
    return slug


def generate_slug(length: int = GENERATED_SLUG_LENGTH) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


@dataclass(frozen=True, slots=True)
class Link:
    slug: str
    url: str
    created_at: datetime
    expires_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class OutboxMessage:
    """An event waiting to be published. `payload` is the JSON-ready event envelope."""

    event_id: UUID
    topic: str
    key: str
    event_type: str
    payload: dict[str, Any]
    created_at: datetime
