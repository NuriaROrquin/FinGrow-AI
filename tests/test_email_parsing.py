from fastapi.testclient import TestClient

URL = "/api/v1/email-parsing/bills"


def test_interpreta_un_mail_con_la_forma_final_del_contrato(client: TestClient) -> None:
    response = client.post(
        URL,
        json={
            "subject": "Tu factura de luz",
            "sender": "edenor.com",
            "body": "Edenor. TOTAL A PAGAR $73.456,92\nVENCIMIENTO 01/10/2026",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "bill"
    assert body["model"]
    bill = body["bill"]
    assert bill["issuer"]
    assert bill["currency"] == "ARS"
    assert bill["category"] == "servicios"
    assert bill["due_date"] == "2026-10-01"
    assert float(bill["amount"]) > 0
    assert 0.0 <= bill["confidence"] <= 1.0


def test_un_cuerpo_vacio_es_rechazado(client: TestClient) -> None:
    response = client.post(URL, json={"subject": "Tu factura", "body": ""})

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_un_cuerpo_demasiado_largo_es_rechazado(client: TestClient) -> None:
    response = client.post(URL, json={"body": "x" * 8001})

    assert response.status_code == 422
