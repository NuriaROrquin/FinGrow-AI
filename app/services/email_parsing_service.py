import json
import logging
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError

from app.core.exceptions import InferenceFailedError
from app.infrastructure.llm.client import LlmClient
from app.infrastructure.prompts.email_parsing import (
    RESPONSE_SCHEMA,
    build_system_prompt,
    build_user_message,
)
from app.schemas.email_parsing import (
    MAX_ISSUER_LENGTH,
    EmailParsingStatus,
    ParseBillEmailRequest,
    ParseBillEmailResponse,
    ParsedBill,
)

logger = logging.getLogger(__name__)

_CENTS = Decimal("0.01")


class EmailParsingService:
    def __init__(self, llm: LlmClient) -> None:
        self._llm = llm

    async def parse_bill(self, request: ParseBillEmailRequest) -> ParseBillEmailResponse:
        logger.info("Interpretando un mail de %d caracteres", len(request.body))

        raw = await self._llm.complete(
            build_user_message(request),
            system=build_system_prompt(request.default_currency),
            response_schema=RESPONSE_SCHEMA,
        )
        model = getattr(self._llm, "model", "unknown")
        payload = self._load(raw)
        status = self._status(payload)

        if status is not EmailParsingStatus.BILL:
            return ParseBillEmailResponse(status=status, model=model)

        amount = self._amount(payload.get("amount"))
        if amount is None:
            return ParseBillEmailResponse(status=EmailParsingStatus.MISSING_AMOUNT, model=model)

        try:
            bill = ParsedBill(
                issuer=self._issuer(payload.get("issuer")),
                amount=amount,
                currency=payload.get("currency") or request.default_currency,
                due_date=self._due_date(payload.get("due_date")),
                category=payload.get("category"),
                confidence=payload.get("confidence"),
            )
        except ValidationError as exc:
            raise InferenceFailedError("El modelo devolvio una factura incompleta o incoherente.") from exc

        return ParseBillEmailResponse(status=status, bill=bill, model=model)

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
    def _status(payload: dict[str, Any]) -> EmailParsingStatus:
        try:
            return EmailParsingStatus(payload.get("status"))
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
    def _issuer(value: Any) -> str:
        return (value.strip() if isinstance(value, str) else "")[:MAX_ISSUER_LENGTH]

    @staticmethod
    def _due_date(value: Any) -> date | None:
        # Un vencimiento ilegible no invalida la factura: el empleado lo ve igual al revisarla.
        if not isinstance(value, str):
            return None

        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            return None
