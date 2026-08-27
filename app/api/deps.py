"""Armado de dependencias.

Es el equivalente a DependencyInjection.cs: el unico lugar donde se decide
como se construye cada pieza. Las rutas piden lo que necesitan con Depends()
y no saben como se fabrica.

Sobre ciclos de vida, que es donde mas se confunde quien viene de .NET:
- Una funcion con Depends() corre una vez por request => equivale a Scoped.
- No hay AddSingleton. El equivalente es crear el objeto una sola vez al
  arrancar (ver el lifespan de main.py) y guardarlo en app.state. Ahi va todo
  lo caro de construir: clientes HTTP, modelos de ML, conexiones.
"""

from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.infrastructure.llm.client import LlmClient
from app.services.categorization_service import CategorizationService

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_llm_client(request: Request) -> LlmClient:
    """Devuelve el cliente creado al arrancar la app (singleton por proceso)."""
    return request.app.state.llm_client


LlmClientDep = Annotated[LlmClient, Depends(get_llm_client)]


def get_categorization_service(llm: LlmClientDep) -> CategorizationService:
    return CategorizationService(llm=llm)


CategorizationServiceDep = Annotated[CategorizationService, Depends(get_categorization_service)]
