from datetime import datetime

from pydantic import AnyHttpUrl, AwareDatetime, BaseModel

from link_service.domain.models import Link


class CreateLinkRequest(BaseModel):
    url: AnyHttpUrl
    slug: str | None = None
    expires_at: AwareDatetime | None = None


class LinkResponse(BaseModel):
    slug: str
    url: str
    short_url: str
    created_at: datetime
    expires_at: datetime | None

    @classmethod
    def from_domain(cls, link: Link, base_url: str) -> "LinkResponse":
        return cls(
            slug=link.slug,
            url=link.url,
            short_url=f"{base_url.rstrip('/')}/{link.slug}",
            created_at=link.created_at,
            expires_at=link.expires_at,
        )
