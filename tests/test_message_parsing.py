from fastapi.testclient import TestClient

URL = "/api/v1/message-parsing/transactions"


def test_interpreta_un_mensaje_con_la_forma_final_del_contrato(client: TestClient) -> None:
    response = client.post(URL, json={"text": "Gaste $500 en supermercado"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "parsed"
    assert body["model"]
    transaction = body["transaction"]
    assert transaction["type"] == "expense"
    assert transaction["currency"] == "ARS"
    assert transaction["expense_category"] == "alimentos"
    assert float(transaction["amount"]) > 0
    assert 0.0 <= transaction["confidence"] <= 1.0


def test_un_texto_vacio_es_rechazado(client: TestClient) -> None:
    response = client.post(URL, json={"text": ""})

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_una_moneda_desconocida_es_rechazada(client: TestClient) -> None:
    response = client.post(URL, json={"text": "Gaste 500", "default_currency": "JPY"})

    assert response.status_code == 422
