from fastapi.testclient import TestClient

URL = "/api/v1/company-insights/recommendations"

_REQUEST = {
    "language": "es",
    "month": "2026-09",
    "measured_employees": 12,
    "average_score": 61.5,
    "participation_rate": 75,
    "concerns": [
        {
            "concern": "thin_cushion",
            "affected_employees": 5,
            "evaluated_employees": 12,
            "percentage": 41.67,
        },
        {
            "concern": "budget_overruns",
            "affected_employees": 3,
            "evaluated_employees": 8,
            "percentage": 37.5,
        },
    ],
}


def test_devuelve_tres_recomendaciones_sin_pantalla(client: TestClient) -> None:
    response = client.post(URL, json=_REQUEST)

    assert response.status_code == 200
    body = response.json()
    assert body["model"]
    assert len(body["recommendations"]) == 3
    for recommendation in body["recommendations"]:
        assert recommendation["kind"] in {"positive", "warning", "tip"}
        assert recommendation["action"] == "none"
        assert recommendation["title"]
        assert recommendation["body"]


def test_sin_preocupaciones_tambien_recomienda(client: TestClient) -> None:
    response = client.post(URL, json={**_REQUEST, "concerns": []})

    assert response.status_code == 200


def test_puntaje_y_participacion_son_opcionales(client: TestClient) -> None:
    optional = {"average_score", "participation_rate"}
    request = {key: value for key, value in _REQUEST.items() if key not in optional}

    response = client.post(URL, json=request)

    assert response.status_code == 200


def test_sin_empleados_medidos_es_rechazado(client: TestClient) -> None:
    response = client.post(URL, json={**_REQUEST, "measured_employees": 0})

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_una_preocupacion_desconocida_es_rechazada(client: TestClient) -> None:
    concerns = [{**_REQUEST["concerns"][0], "concern": "deudas"}]

    response = client.post(URL, json={**_REQUEST, "concerns": concerns})

    assert response.status_code == 422


def test_una_preocupacion_repetida_es_rechazada(client: TestClient) -> None:
    concerns = [_REQUEST["concerns"][0], _REQUEST["concerns"][0]]

    response = client.post(URL, json={**_REQUEST, "concerns": concerns})

    assert response.status_code == 422


def test_mas_afectados_que_evaluados_es_rechazado(client: TestClient) -> None:
    concerns = [{**_REQUEST["concerns"][0], "affected_employees": 13}]

    response = client.post(URL, json={**_REQUEST, "concerns": concerns})

    assert response.status_code == 422


def test_mas_evaluados_que_medidos_es_rechazado(client: TestClient) -> None:
    concerns = [{**_REQUEST["concerns"][0], "evaluated_employees": 13}]

    response = client.post(URL, json={**_REQUEST, "concerns": concerns})

    assert response.status_code == 422


def test_un_porcentaje_fuera_de_rango_es_rechazado(client: TestClient) -> None:
    concerns = [{**_REQUEST["concerns"][0], "percentage": 101}]

    response = client.post(URL, json={**_REQUEST, "concerns": concerns})

    assert response.status_code == 422


def test_un_mes_mal_formado_es_rechazado(client: TestClient) -> None:
    response = client.post(URL, json={**_REQUEST, "month": "2026-9"})

    assert response.status_code == 422
