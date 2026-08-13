from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint_exposes_scaffold_metadata() -> None:
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "scaffolded"
    assert payload["health"] == "/api/v1/health"


def test_health_endpoint_reports_subsystem_boundaries() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["api"]["status"] == "ok"
    assert payload["database"]["status"] == "pending"
    assert payload["machine_learning"]["status"] == "pending"
