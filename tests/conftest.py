import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture(autouse=True)
def _settings_de_test(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.setenv("API_KEY", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    # TestClient dispara el lifespan al usarse como context manager, asi que
    # app.state.llm_client queda disponible igual que en produccion.
    with TestClient(create_app()) as test_client:
        yield test_client
