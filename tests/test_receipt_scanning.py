from datetime import date

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app

URL = "/api/v1/receipt-scanning/receipts"
JPEG = b"\xff\xd8\xff\xe0receipt"


def test_escanea_un_comprobante_con_la_forma_final_del_contrato(client: TestClient) -> None:
    response = client.post(URL, files={"file": ("ticket.jpg", JPEG, "image/jpeg")})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "parsed"
    assert body["model"] == f"stub-ocr+{get_settings().llm_model}"
    assert body["receipt"] == {
        "merchant": "Supermercado Día",
        "amount": "1250.50",
        "currency": "ARS",
        "occurred_on": date.today().isoformat(),
        "category": "alimentos",
        "payment_method": "debit_card",
        "confidence": 0.93,
    }


def test_usa_la_moneda_por_defecto_que_manda_el_backend(client: TestClient) -> None:
    response = client.post(
        URL,
        files={"file": ("ticket.jpg", JPEG, "image/jpeg")},
        data={"default_currency": "USD"},
    )

    assert response.status_code == 200
    assert response.json()["receipt"]["currency"] == "USD"


def test_un_formato_no_soportado_responde_415(client: TestClient) -> None:
    response = client.post(URL, files={"file": ("ticket.webp", b"RIFF....WEBP", "image/webp")})

    assert response.status_code == 415
    assert response.json()["code"] == "unsupported_document"


def test_un_comprobante_vacio_responde_422(client: TestClient) -> None:
    response = client.post(URL, files={"file": ("ticket.jpg", b"", "image/jpeg")})

    assert response.status_code == 422
    assert response.json()["code"] == "document_not_readable"


def test_sin_archivo_no_cumple_el_contrato(client: TestClient) -> None:
    response = client.post(URL)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_un_comprobante_mas_grande_que_el_maximo_responde_413() -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(ocr_max_document_bytes=4)

    with TestClient(app) as test_client:
        response = test_client.post(URL, files={"file": ("ticket.jpg", JPEG, "image/jpeg")})

    assert response.status_code == 413
    assert response.json()["code"] == "document_too_large"


def test_exige_la_api_key_cuando_esta_configurada() -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(api_key="secreto")

    with TestClient(app) as test_client:
        response = test_client.post(URL, files={"file": ("ticket.jpg", JPEG, "image/jpeg")})

    assert response.status_code == 401
