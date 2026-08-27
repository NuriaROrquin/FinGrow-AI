"""Acceso al proveedor de IA.

`LlmClient` es el contrato: el equivalente a una interface de
FinGrow.Application/Interfaces. Los servicios dependen de esto, no de una
implementacion concreta, asi cambiar de proveedor no toca la capa de
servicios.

Un Protocol es una interface estructural: una clase lo cumple con solo tener
los metodos con la firma correcta, sin heredar de nada.
"""

from typing import Protocol

from app.core.config import Settings


class LlmClient(Protocol):
    async def complete(self, prompt: str) -> str:
        """Manda un prompt al modelo y devuelve el texto crudo de la respuesta."""
        ...

    async def is_available(self) -> bool:
        """True si el proveedor esta respondiendo."""
        ...


class StubLlmClient:
    """Implementacion falsa para desarrollo y tests.

    Permite levantar la API y que el equipo de .NET integre contra el contrato
    real mientras la IA de verdad todavia se esta resolviendo.
    """

    def __init__(self, model: str) -> None:
        self.model = model

    async def complete(self, prompt: str) -> str:
        return "stub"

    async def is_available(self) -> bool:
        return True


class AnthropicLlmClient:
    """Cliente real. TODO: implementar cuando definamos el primer caso de uso.

    Nota de rendimiento para cuando se implemente: si se usa un cliente HTTP
    async, este metodo va como `async def`. Si se termina usando una libreria
    que bloquea, la ruta que lo consuma tiene que declararse `def` (sin async)
    para que FastAPI la mande a un hilo aparte y no frene el resto de la API.
    """

    def __init__(self, api_key: str, model: str, timeout_seconds: int) -> None:
        self._api_key = api_key
        self.model = model
        self._timeout_seconds = timeout_seconds

    async def complete(self, prompt: str) -> str:
        raise NotImplementedError("Cliente real de Anthropic pendiente.")

    async def is_available(self) -> bool:
        raise NotImplementedError("Cliente real de Anthropic pendiente.")


def build_llm_client(settings: Settings) -> LlmClient:
    """Elige la implementacion segun la config.

    Es el unico lugar del codigo que sabe que proveedores existen.
    """
    if settings.llm_provider == "anthropic":
        return AnthropicLlmClient(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    return StubLlmClient(model=settings.llm_model)
