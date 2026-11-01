class DomainError(Exception):
    """Base class for business rule violations."""


class InvalidSlugError(DomainError):
    pass


class InvalidExpirationError(DomainError):
    pass


class SlugAlreadyExistsError(DomainError):
    def __init__(self, slug: str) -> None:
        super().__init__(f"slug '{slug}' is already taken")
        self.slug = slug


class LinkNotFoundError(DomainError):
    def __init__(self, slug: str) -> None:
        super().__init__(f"link '{slug}' not found")
        self.slug = slug
