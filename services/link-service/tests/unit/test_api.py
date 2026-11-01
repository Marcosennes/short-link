import pytest
from fastapi.testclient import TestClient

from link_service.config import Settings
from link_service.main import create_app


@pytest.fixture
def client(uow_factory):
    settings = Settings(public_base_url="http://short.test/r/")
    with TestClient(create_app(settings, uow_factory=uow_factory)) as client:
        yield client


def test_create_link_returns_201_with_short_url(client, db):
    response = client.post("/links", json={"url": "https://example.com/a", "slug": "abc"})

    assert response.status_code == 201
    body = response.json()
    assert body["slug"] == "abc"
    assert body["url"] == "https://example.com/a"
    assert body["short_url"] == "http://short.test/r/abc"
    assert body["expires_at"] is None
    assert len(db.pending()) == 1


def test_create_link_generates_slug(client):
    response = client.post("/links", json={"url": "https://example.com"})

    assert response.status_code == 201
    assert len(response.json()["slug"]) == 7


def test_create_link_with_expiration(client):
    response = client.post(
        "/links", json={"url": "https://example.com", "expires_at": "2999-01-01T00:00:00Z"}
    )

    assert response.status_code == 201
    assert response.json()["expires_at"].startswith("2999-01-01")


@pytest.mark.parametrize(
    "body",
    [
        {"url": "not-a-url"},
        {"url": "ftp://example.com"},
        {"url": "https://example.com", "slug": "a b"},
        {"url": "https://example.com", "expires_at": "2999-01-01T00:00:00"},  # naive
        {"url": "https://example.com", "expires_at": "2000-01-01T00:00:00Z"},  # past
    ],
)
def test_create_link_rejects_invalid_input(client, body):
    assert client.post("/links", json=body).status_code == 422


def test_create_link_with_taken_slug_returns_409(client):
    client.post("/links", json={"url": "https://a.com", "slug": "dup"})

    response = client.post("/links", json={"url": "https://b.com", "slug": "dup"})

    assert response.status_code == 409
    assert "dup" in response.json()["detail"]


def test_get_link(client):
    client.post("/links", json={"url": "https://a.com", "slug": "find"})

    response = client.get("/links/find")

    assert response.status_code == 200
    assert response.json()["url"] == "https://a.com/"


def test_get_missing_link_returns_404(client):
    assert client.get("/links/missing").status_code == 404


def test_list_links_paginates(client):
    for slug in ("aaa", "bbb", "ccc"):
        client.post("/links", json={"url": "https://a.com", "slug": slug})

    assert len(client.get("/links").json()) == 3
    assert len(client.get("/links", params={"limit": 2}).json()) == 2
    assert client.get("/links", params={"limit": 0}).status_code == 422


def test_delete_link(client, db):
    client.post("/links", json={"url": "https://a.com", "slug": "bye"})

    assert client.delete("/links/bye").status_code == 204
    assert client.get("/links/bye").status_code == 404
    assert [m.event_type for m in db.pending()] == ["link.created", "link.deleted"]


def test_delete_missing_link_returns_404(client):
    assert client.delete("/links/ghost").status_code == 404
