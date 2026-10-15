from fastapi.testclient import TestClient

URL = "/api/v1/financial-insights/recommendations"

_REQUEST = {
    "language": "es",
    "currency": "ARS",
    "period_start": "2026-09-01",
    "period_end": "2026-10-15",
    "months": [
        {
            "month": "2026-08",
            "is_reference": True,
            "income": 900000,
            "expenses": 700000,
            "savings": 200000,
            "expenses_by_category": [{"category": "alimentos", "amount": 300000}],
        },
        {
            "month": "2026-09",
            "income": 1000000,
            "expenses": 800000,
            "savings": 250000,
            "expenses_by_category": [
                {"category": "alimentos", "amount": 350000},
                {"category": "ahorro_inversion", "amount": 50000},
            ],
        },
    ],
    "budget_limits": [{"category": "alimentos", "limit": 300000, "spent": 350000}],
    "goals": [
        {
            "name": "Vacaciones",
            "status": "active",
            "target_amount": 1200000,
            "current_amount": 300000,
            "monthly_commitment": 100000,
            "deadline": "2027-06-30",
        }
    ],
}


def test_devuelve_tres_recomendaciones_con_la_forma_final_del_contrato(client: TestClient) -> None:
    response = client.post(URL, json=_REQUEST)

    assert response.status_code == 200
    body = response.json()
    assert body["model"]
    assert len(body["recommendations"]) == 3
    for recommendation in body["recommendations"]:
        assert recommendation["kind"] in {"positive", "warning", "tip"}
        assert recommendation["action"] in {"budgets", "goals", "transactions", "education", "none"}
        assert recommendation["title"]
        assert recommendation["body"]


def test_alcanza_con_un_mes_sin_presupuesto_ni_metas(client: TestClient) -> None:
    request = {**_REQUEST, "months": _REQUEST["months"][1:], "budget_limits": [], "goals": []}

    response = client.post(URL, json=request)

    assert response.status_code == 200


def test_sin_meses_es_rechazado(client: TestClient) -> None:
    response = client.post(URL, json={**_REQUEST, "months": []})

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_un_periodo_invertido_es_rechazado(client: TestClient) -> None:
    response = client.post(URL, json={**_REQUEST, "period_start": "2026-10-15", "period_end": "2026-09-01"})

    assert response.status_code == 422


def test_un_idioma_desconocido_es_rechazado(client: TestClient) -> None:
    response = client.post(URL, json={**_REQUEST, "language": "fr"})

    assert response.status_code == 422


def test_una_categoria_desconocida_es_rechazada(client: TestClient) -> None:
    months = [{**_REQUEST["months"][1], "expenses_by_category": [{"category": "Alimentos", "amount": 1}]}]

    response = client.post(URL, json={**_REQUEST, "months": months})

    assert response.status_code == 422


def test_un_mes_mal_escrito_es_rechazado(client: TestClient) -> None:
    months = [{**_REQUEST["months"][1], "month": "2026-13"}]

    response = client.post(URL, json={**_REQUEST, "months": months})

    assert response.status_code == 422
