from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from link_service.domain.errors import (
    DomainError,
    InvalidExpirationError,
    InvalidSlugError,
    LinkNotFoundError,
    SlugAlreadyExistsError,
)

_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    LinkNotFoundError: status.HTTP_404_NOT_FOUND,
    SlugAlreadyExistsError: status.HTTP_409_CONFLICT,
    InvalidSlugError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    InvalidExpirationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


async def _handle_domain_error(_: Request, error: Exception) -> JSONResponse:
    code = _STATUS_BY_ERROR.get(type(error), status.HTTP_400_BAD_REQUEST)
    return JSONResponse(status_code=code, content={"detail": str(error)})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _handle_domain_error)
