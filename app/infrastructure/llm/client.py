"""Acceso al proveedor de IA.

`LlmClient` es el contrato: el equivalente a una interface de
FinGrow.Application/Interfaces. Los servicios dependen de esto, no de una
implementacion concreta, asi cambiar de proveedor no toca la capa de
servicios.

Un Protocol es una interface estructural: una clase lo cumple con solo tener
los metodos con la firma correcta, sin heredar de nada.
"""

import json
import logging
from typing import Any, Protocol

import anthropic
from anthropic import AsyncAnthropic

from app.core.config import Settings
from app.core.exceptions import InferenceFailedError, ModelUnavailableError

logger = logging.getLogger(__name__)

_MAX_TOKENS = 4096
_PING_PROMPT = "Respondiendo esto confirmo que el servicio esta arriba. Contesta 'ok'."


class LlmClient(Protocol):
    async def complete(
        self, prompt: str, *, system: str | None = None, response_schema: dict[str, Any] | None = None
    ) -> str:
        """Manda un prompt al modelo y devuelve el texto crudo de la respuesta.

        `system` son instrucciones fijas, separadas del contenido variable de
        `prompt`. `response_schema` es un JSON Schema opcional: si se pasa, la
        implementacion fuerza que la respuesta cumpla esa forma y devuelve el
        JSON resultante como texto -- el cliente no sabe que representa ese
        JSON ni a que caso de uso pertenece, eso lo interpreta quien llama.
        """
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

    async def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        if response_schema is None:
            return "stub"
        return self._fake_structured_response(prompt, response_schema)

    async def is_available(self) -> bool:
        return True

    @staticmethod
    def _fake_structured_response(prompt: str, response_schema: dict[str, Any]) -> str:
        """Devuelve un JSON con la forma de `response_schema`, sin llamar a ningun modelo.

        Introspecciona lo minimo indispensable del schema (un array
        "results" con "id"/"category"/"confidence" por entrada) para que el
        equipo de .NET pueda integrar contra la forma final de la respuesta
        HTTP mientras la IA real no esta resuelta -- el mismo rol que ya
        cumplia el stub antes de este ticket, ahora con la forma correcta.
        """
        try:
            entries = json.loads(prompt)["transactions"]
        except (json.JSONDecodeError, KeyError, TypeError):
            entries = []

        category_enum = (
            response_schema.get("properties", {})
            .get("results", {})
            .get("items", {})
            .get("properties", {})
            .get("category", {})
            .get("enum", ["otros"])
        )

        results = [{"id": entry["id"], "category": category_enum[0], "confidence": 0.0} for entry in entries]
        return json.dumps({"results": results})


class AnthropicLlmClient:
    """
    Cliente real contra la API de Anthropic, via `AsyncAnthropic`.
    """

    def __init__(self, api_key: str, model: str, timeout_seconds: int) -> None:
        self._client = AsyncAnthropic(api_key=api_key, timeout=timeout_seconds)
        self.model = model

    async def complete(
        self, prompt: str, *, system: str | None = None, response_schema: dict[str, Any] | None = None
    ) -> str:
        create_kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": _MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system is not None:
            create_kwargs["system"] = system

        tool_name = "emit_structured_response"
        if response_schema is not None:
            create_kwargs["tools"] = [
                {
                    "name": tool_name,
                    "description": "Devuelve el resultado con la forma pedida.",
                    "input_schema": response_schema,
                }
            ]
            create_kwargs["tool_choice"] = {"type": "tool", "name": tool_name}

        try:
            message = await self._client.messages.create(**create_kwargs)
        except (anthropic.APITimeoutError, anthropic.APIConnectionError) as exc:
            raise ModelUnavailableError("El proveedor de IA no respondio a tiempo.") from exc
        except anthropic.RateLimitError as exc:
            raise ModelUnavailableError(
                "El proveedor de IA esta limitando las requests (rate limit)."
            ) from exc
        except anthropic.AuthenticationError as exc:
            logger.error("LLM_API_KEY invalida o vencida: %s", exc)
            raise ModelUnavailableError("El proveedor de IA rechazo las credenciales.") from exc
        except anthropic.APIStatusError as exc:
            if exc.status_code >= 500:
                raise ModelUnavailableError("El proveedor de IA respondio con un error interno.") from exc
            raise

        if response_schema is not None:
            tool_use = next((block for block in message.content if block.type == "tool_use"), None)
            if tool_use is None:
                raise InferenceFailedError("El modelo no invoco la respuesta estructurada pedida.")
            return json.dumps(tool_use.input)

        text_block = next((block for block in message.content if block.type == "text"), None)
        if text_block is None:
            raise InferenceFailedError("El modelo no devolvio texto interpretable.")
        return text_block.text

    async def is_available(self) -> bool:
        try:
            await self.complete(_PING_PROMPT)
        except ModelUnavailableError:
            return False
        except InferenceFailedError:
            return True
        return True


def build_llm_client(settings: Settings) -> LlmClient:
    """
    Elige la implementacion segun la config.
    """
    if settings.llm_provider == "anthropic":
        return AnthropicLlmClient(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    return StubLlmClient(model=settings.llm_model)
