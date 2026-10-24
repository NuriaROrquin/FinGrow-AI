from fastapi.testclient import TestClient

URL = "/api/v1/budget-insights/recommendations"

_REQUEST = {
    "language": "es",
    "currency": "ARS",
    "months": [
        {
            "month": "2026-08",
            "limits": [
                {"category": "alimentos", "limit": 300000, "spent": 340000},
                {"category": "entretenimiento", "limit": 50000, "spent": 20000},
            ],
            "unbudgeted_expenses": [{"category": "transporte", "amount": 90000}],
        },
        {
            "month": "2026-09",
            "limits": [{"category": "alimentos", "limit": 300000, "spent": 310000}],
        },
        {
            "month": "2026-10",
            "is_current": True,
            "limits": [{"category": "alimentos", "limit": 300000, "spent": 120000}],
        },
    ],
}


def test_devuelve_tres_recomendaciones_con_la_forma_del_contrato(client: TestClient) -> None:
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


def test_sin_meses_es_rechazado(client: TestClient) -> None:
    response = client.post(URL, json={**_REQUEST, "months": []})

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_un_mes_sin_topes_es_rechazado(client: TestClient) -> None:
    months = [{**_REQUEST["months"][0], "limits": []}]

    response = client.post(URL, json={**_REQUEST, "months": months})

    assert response.status_code == 422


def test_un_tope_en_cero_es_rechazado(client: TestClient) -> None:
    months = [{**_REQUEST["months"][0], "limits": [{"category": "alimentos", "limit": 0, "spent": 10}]}]

    response = client.post(URL, json={**_REQUEST, "months": months})

    assert response.status_code == 422


def test_un_mes_repetido_es_rechazado(client: TestClient) -> None:
    months = [_REQUEST["months"][0], _REQUEST["months"][0]]

    response = client.post(URL, json={**_REQUEST, "months": months})

    assert response.status_code == 422


def test_dos_meses_en_curso_son_rechazados(client: TestClient) -> None:
    months = [{**month, "is_current": True} for month in _REQUEST["months"][:2]]

    response = client.post(URL, json={**_REQUEST, "months": months})

    assert response.status_code == 422


def test_mas_de_doce_meses_es_rechazado(client: TestClient) -> None:
    months = [{**_REQUEST["months"][1], "month": f"2025-{index:02d}"} for index in range(1, 13)]
    months.append({**_REQUEST["months"][1], "month": "2026-01"})

    response = client.post(URL, json={**_REQUEST, "months": months})

    assert response.status_code == 422


def test_una_categoria_desconocida_es_rechazada(client: TestClient) -> None:
    months = [{**_REQUEST["months"][0], "limits": [{"category": "Alimentos", "limit": 1, "spent": 0}]}]

    response = client.post(URL, json={**_REQUEST, "months": months})

    assert response.status_code == 422
