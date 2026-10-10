import json
import logging
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError

from app.core.exceptions import InferenceFailedError
from app.infrastructure.llm.client import LlmClient
from app.infrastructure.prompts.message_parsing import (
    RESPONSE_SCHEMA,
    build_system_prompt,
    build_user_message,
)
from app.schemas.message_parsing import (
    MAX_DESCRIPTION_LENGTH,
    MessageParsingStatus,
    ParsedTransaction,
    ParseMessageRequest,
    ParseMessageResponse,
)

logger = logging.getLogger(__name__)

_CENTS = Decimal("0.01")


class MessageParsingService:
    def __init__(self, llm: LlmClient) -> None:
        self._llm = llm

    async def parse(self, request: ParseMessageRequest) -> ParseMessageResponse:
        logger.info("Interpretando un mensaje de %d caracteres", len(request.text))

        raw = await self._llm.complete(
            build_user_message(request),
            system=build_system_prompt(request.default_currency),
            response_schema=RESPONSE_SCHEMA,
        )
        model = getattr(self._llm, "model", "unknown")
        payload = self._load(raw)
        status = self._status(payload)

        if status is not MessageParsingStatus.PARSED:
            return ParseMessageResponse(status=status, model=model)

        amount = self._amount(payload.get("amount"))
        if amount is None:
            return ParseMessageResponse(status=MessageParsingStatus.MISSING_AMOUNT, model=model)

        try:
            transaction = ParsedTransaction(
                type=payload.get("type"),
                amount=amount,
                currency=payload.get("currency") or request.default_currency,
                expense_category=payload.get("expense_category"),
                income_category=payload.get("income_category"),
                description=self._description(payload.get("description"), request.text),
                payment_method=payload.get("payment_method"),
                confidence=payload.get("confidence"),
            )
        except ValidationError as exc:
            raise InferenceFailedError("El modelo devolvio un movimiento incompleto o incoherente.") from exc

        return ParseMessageResponse(status=status, transaction=transaction, model=model)

    @staticmethod
    def _load(raw: str) -> dict[str, Any]:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise InferenceFailedError("La respuesta del modelo no tiene el formato esperado.") from exc

        if not isinstance(payload, dict):
            raise InferenceFailedError("La respuesta del modelo no tiene el formato esperado.")

        return payload

    @staticmethod
    def _status(payload: dict[str, Any]) -> MessageParsingStatus:
        try:
            return MessageParsingStatus(payload.get("status"))
        except ValueError as exc:
            raise InferenceFailedError("El modelo devolvio un status desconocido.") from exc

    @staticmethod
    def _amount(value: Any) -> Decimal | None:
        if value is None or isinstance(value, bool):
            return None

        try:
            amount = abs(Decimal(str(value))).quantize(_CENTS, rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError):
            return None

        return amount if amount > 0 else None

    @staticmethod
    def _description(value: Any, text: str) -> str:
        description = value.strip() if isinstance(value, str) else ""

        return (description or text.strip())[:MAX_DESCRIPTION_LENGTH]
