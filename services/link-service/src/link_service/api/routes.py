from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from link_service.api.schemas import CreateLinkRequest, LinkResponse
from link_service.service import LinkService

router = APIRouter(prefix="/links", tags=["links"])


def get_service(request: Request) -> LinkService:
    return request.app.state.link_service


def get_base_url(request: Request) -> str:
    return request.app.state.settings.public_base_url


Service = Annotated[LinkService, Depends(get_service)]
BaseUrl = Annotated[str, Depends(get_base_url)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_link(body: CreateLinkRequest, service: Service, base_url: BaseUrl) -> LinkResponse:
    link = await service.create(str(body.url), slug=body.slug, expires_at=body.expires_at)
    return LinkResponse.from_domain(link, base_url)


@router.get("")
async def list_links(
    service: Service,
    base_url: BaseUrl,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[LinkResponse]:
    links = await service.list(limit=limit, offset=offset)
    return [LinkResponse.from_domain(link, base_url) for link in links]


@router.get("/{slug}")
async def get_link(slug: str, service: Service, base_url: BaseUrl) -> LinkResponse:
    return LinkResponse.from_domain(await service.get(slug), base_url)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(slug: str, service: Service) -> None:
    await service.delete(slug)
