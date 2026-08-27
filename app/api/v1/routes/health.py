"""Health check.

Se monta en la raiz (/health), NO bajo /api/v1, porque el backend .NET ya lo
consume asi: ver AiService.IsHealthyAsync en FinGrow.Infrastructure/Ai.

Tampoco pide API key: un chequeo de vida tiene que poder hacerlo el
orquestador (Docker, Kubernetes) sin credenciales.
"""

from fastapi import APIRouter

from app.api.deps import SettingsDep
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.environment,
    )
