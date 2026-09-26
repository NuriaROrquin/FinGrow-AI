"""Caso de uso: categorizar un lote de movimientos.

Equivale a un Feature/Handler de FinGrow.Application. Orquesta: valida lo que
Pydantic no puede validar solo, arma el prompt, llama al modelo, interpreta la
respuesta. No sabe nada de HTTP -- eso es responsabilidad de la capa api/.
"""

import json
import logging
from uuid import UUID

from app.core.exceptions import InferenceFailedError
from app.domain.enums import ExpenseCategory
from app.infrastructure.llm.client import LlmClient
from app.infrastructure.prompts.categorization import (
    RESPONSE_SCHEMA,
    build_system_prompt,
    build_user_message,
)
from app.schemas.categorization import (
    CategorizedTransaction,
    CategorizeRequest,
    CategorizeResponse,
)

logger = logging.getLogger(__name__)


class CategorizationService:
    def __init__(self, llm: LlmClient) -> None:
        self._llm = llm

    async def categorize(self, request: CategorizeRequest) -> CategorizeResponse:
        logger.info("Categorizando %d movimientos", len(request.transactions))

        raw = await self._llm.complete(
            build_user_message(request.transactions),
            system=build_system_prompt(),
            response_schema=RESPONSE_SCHEMA,
        )
        results = self._parse_results(raw, expected_ids={t.id for t in request.transactions})

        return CategorizeResponse(results=results, model=getattr(self._llm, "model", "unknown"))

    def _parse_results(self, raw: str, expected_ids: set[UUID]) -> list[CategorizedTransaction]:
        try:
            payload = json.loads(raw)
            entries = payload["results"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise InferenceFailedError("La respuesta del modelo no tiene el formato esperado.") from exc

        try:
            results = [
                CategorizedTransaction(
                    id=UUID(entry["id"]),
                    category=ExpenseCategory(entry["category"]),
                    confidence=entry["confidence"],
                )
                for entry in entries
            ]
        except (KeyError, ValueError, TypeError) as exc:
            raise InferenceFailedError("El modelo devolvio un id, categoria o confidence invalido.") from exc

        result_ids = {result.id for result in results}
        if result_ids != expected_ids:
            raise InferenceFailedError(
                "El modelo no devolvio exactamente un resultado por cada movimiento recibido."
            )

        return results
