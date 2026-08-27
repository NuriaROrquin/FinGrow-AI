from fastapi.testclient import TestClient

PAYLOAD = {
    "transactions": [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "description": "Supermercado Coto",
            "amount": "-15400.50",
            "currency": "ARS",
            "occurred_on": "2026-08-20",
            "merchant": "COTO CICSA",
        }
    ]
}


def test_categorize_devuelve_un_resultado_por_movimiento(client: TestClient) -> None:
    response = client.post("/api/v1/categorization/transactions", json=PAYLOAD)

    assert response.status_code == 200
    assert len(response.json()["results"]) == 1


def test_lote_vacio_es_rechazado(client: TestClient) -> None:
    """Pydantic corta el request antes de llegar al service."""
    response = client.post("/api/v1/categorization/transactions", json={"transactions": []})

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
