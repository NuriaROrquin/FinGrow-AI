"""Tests de AnthropicLlmClient con el SDK mockeado -- nunca pegan a la red real."""

import json
from unittest.mock import AsyncMock

import anthropic
import httpx2
import pytest

from app.core.exceptions import InferenceFailedError, ModelUnavailableError
from app.infrastructure.llm.client import AnthropicLlmClient


class _FakeTextBlock:
    type = "text"

    def __init__(self, text: str) -> None:
        self.text = text


class _FakeToolUseBlock:
    type = "tool_use"

    def __init__(self, input_: dict) -> None:
        self.input = input_


class _FakeMessage:
    def __init__(self, content: list) -> None:
        self.content = content


def _make_client() -> AnthropicLlmClient:
    return AnthropicLlmClient(api_key="test-key", model="claude-sonnet-5", timeout_seconds=5)


def _status_error(cls: type[anthropic.APIStatusError], status_code: int) -> anthropic.APIStatusError:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx2.Response(status_code, request=request)
    return cls("boom", response=response, body=None)


async def test_complete_devuelve_el_texto_de_la_respuesta() -> None:
    client = _make_client()
    client._client.messages.create = AsyncMock(return_value=_FakeMessage([_FakeTextBlock("hola")]))

    result = await client.complete("prompt")

    assert result == "hola"


async def test_complete_con_response_schema_devuelve_el_json_del_tool_use() -> None:
    client = _make_client()
    client._client.messages.create = AsyncMock(
        return_value=_FakeMessage([_FakeToolUseBlock({"results": []})])
    )

    result = await client.complete("prompt", response_schema={"type": "object"})

    assert json.loads(result) == {"results": []}


async def test_timeout_lanza_model_unavailable() -> None:
    client = _make_client()
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    client._client.messages.create = AsyncMock(side_effect=anthropic.APITimeoutError(request=request))

    with pytest.raises(ModelUnavailableError):
        await client.complete("prompt")


async def test_error_5xx_lanza_model_unavailable() -> None:
    client = _make_client()
    client._client.messages.create = AsyncMock(side_effect=_status_error(anthropic.APIStatusError, 500))

    with pytest.raises(ModelUnavailableError):
        await client.complete("prompt")


async def test_error_4xx_no_mapeado_se_propaga_tal_cual() -> None:
    client = _make_client()
    client._client.messages.create = AsyncMock(side_effect=_status_error(anthropic.APIStatusError, 400))

    with pytest.raises(anthropic.APIStatusError):
        await client.complete("prompt")


async def test_rate_limit_lanza_model_unavailable() -> None:
    client = _make_client()
    client._client.messages.create = AsyncMock(side_effect=_status_error(anthropic.RateLimitError, 429))

    with pytest.raises(ModelUnavailableError):
        await client.complete("prompt")


async def test_authentication_error_lanza_model_unavailable() -> None:
    client = _make_client()
    client._client.messages.create = AsyncMock(side_effect=_status_error(anthropic.AuthenticationError, 401))

    with pytest.raises(ModelUnavailableError):
        await client.complete("prompt")


async def test_respuesta_estructurada_sin_tool_use_lanza_inference_failed() -> None:
    client = _make_client()
    client._client.messages.create = AsyncMock(
        return_value=_FakeMessage([_FakeTextBlock("no invoco la tool")])
    )

    with pytest.raises(InferenceFailedError):
        await client.complete("prompt", response_schema={"type": "object"})


async def test_is_available_true_en_caso_feliz() -> None:
    client = _make_client()
    client._client.messages.create = AsyncMock(return_value=_FakeMessage([_FakeTextBlock("ok")]))

    assert await client.is_available() is True


async def test_is_available_false_si_el_proveedor_no_responde() -> None:
    client = _make_client()
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    client._client.messages.create = AsyncMock(side_effect=anthropic.APIConnectionError(request=request))

    assert await client.is_available() is False
