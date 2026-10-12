from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.infrastructure.transcription.client import STUB_TRANSCRIPT
from app.main import create_app

URL = "/api/v1/transcription/audio"


def test_transcribe_una_nota_de_voz_con_la_forma_final_del_contrato(client: TestClient) -> None:
    response = client.post(URL, files={"file": ("nota.ogg", b"OggS-audio", "audio/ogg")})

    assert response.status_code == 200
    assert response.json() == {
        "text": STUB_TRANSCRIPT,
        "language": "es",
        "model": get_settings().transcription_model,
    }


def test_un_formato_no_soportado_responde_415(client: TestClient) -> None:
    response = client.post(URL, files={"file": ("nota.amr", b"#!AMR", "audio/amr")})

    assert response.status_code == 415
    assert response.json()["code"] == "unsupported_audio"


def test_un_audio_vacio_responde_audio_not_understood(client: TestClient) -> None:
    response = client.post(URL, files={"file": ("nota.ogg", b"", "audio/ogg")})

    assert response.status_code == 422
    assert response.json()["code"] == "audio_not_understood"


def test_sin_archivo_no_cumple_el_contrato(client: TestClient) -> None:
    response = client.post(URL)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_un_audio_mas_grande_que_el_maximo_responde_413() -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(transcription_max_audio_bytes=4)

    with TestClient(app) as test_client:
        response = test_client.post(URL, files={"file": ("nota.ogg", b"OggS-audio", "audio/ogg")})

    assert response.status_code == 413
    assert response.json()["code"] == "audio_too_large"


def test_exige_la_api_key_cuando_esta_configurada() -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(api_key="secreto")

    with TestClient(app) as test_client:
        response = test_client.post(URL, files={"file": ("nota.ogg", b"OggS-audio", "audio/ogg")})

    assert response.status_code == 401
