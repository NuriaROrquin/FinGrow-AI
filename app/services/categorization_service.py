"""Caso de uso: categorizar un lote de movimientos.

Equivale a un Feature/Handler de FinGrow.Application. Orquesta: valida lo que
Pydantic no puede validar solo, arma el prompt, llama al modelo, interpreta la
respuesta. No sabe nada de HTTP -- eso es responsabilidad de la capa api/.
"""

import logging

from app.domain.enums import ExpenseCategory
from app.infrastructure.llm.client import LlmClient
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

        # TODO: armar el prompt (app/infrastructure/prompts/), llamar a
        # self._llm.complete() e interpretar la respuesta.
        # Por ahora devolvemos una respuesta con la forma final del contrato
        # para que el backend .NET pueda integrar en paralelo.
        results = [
            CategorizedTransaction(
                id=transaction.id,
                category=ExpenseCategory.OTROS,
                confidence=0.0,
            )
            for transaction in request.transactions
        ]

        return CategorizeResponse(results=results, model=getattr(self._llm, "model", "unknown"))
