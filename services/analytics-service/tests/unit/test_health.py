from fastapi.testclient import TestClient

from analytics_service.main import create_app


def test_health_returns_ok():
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "analytics-service"}
