import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    # TestClient dispara el lifespan al usarse como context manager, asi que
    # app.state.llm_client queda disponible igual que en produccion.
    with TestClient(create_app()) as test_client:
        yield test_client
