from unittest.mock import MagicMock, Mock, patch

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

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


def test_root_health_endpoint_reports_healthy_status() -> None:
    fake_connection = Mock()
    fake_engine = MagicMock()
    fake_engine.connect.return_value.__enter__.return_value = fake_connection
    fake_engine.connect.return_value.__exit__.return_value = None

    with patch("app.main.get_engine", return_value=fake_engine):
        response = client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "healthy"}
    fake_connection.execute.assert_called_once()


def test_root_health_endpoint_returns_unhealthy_when_database_is_unreachable() -> None:
    fake_engine = Mock()
    fake_engine.connect.side_effect = OperationalError("SELECT 1", {}, Exception("database unavailable"))

    with patch("app.main.get_engine", return_value=fake_engine):
        response = client.get("/health")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {"detail": "Database connectivity check failed."}
