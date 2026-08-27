from fastapi.testclient import TestClient


def test_health_responde_ok(client: TestClient) -> None:
    """Contrato con AiService.IsHealthyAsync del backend .NET."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
