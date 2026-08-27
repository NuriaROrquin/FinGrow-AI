"""Contrato del endpoint de categorizacion.

Endpoint de ejemplo: sirve como molde para los que vengan.

En .NET un DTO es una clase y la validacion va aparte, en Validators. Aca son
la misma cosa: si el request no cumple estas restricciones, FastAPI responde
422 antes de que se ejecute una sola linea nuestra.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import ExpenseCategory


class TransactionInput(BaseModel):
    """Un movimiento a categorizar.

    Mandamos lo minimo indispensable para inferir la categoria: nada de
    nombre, mail ni datos de cuenta. Lo que no viaja no se filtra.
    """

    id: UUID = Field(description="Id del movimiento en la base del backend.")
    description: str = Field(min_length=1, max_length=500)
    amount: Decimal = Field(description="Monto. Negativo = gasto, positivo = ingreso.")
    currency: str = Field(default="ARS", min_length=3, max_length=3)
    occurred_on: date
    merchant: str | None = Field(default=None, max_length=200)


class CategorizeRequest(BaseModel):
    transactions: list[TransactionInput] = Field(
        min_length=1,
        max_length=200,
        description="Lote de movimientos. El tope evita requests que tarden de mas.",
    )


class CategorizedTransaction(BaseModel):
    id: UUID
    category: ExpenseCategory
    confidence: float = Field(ge=0.0, le=1.0)


class CategorizeResponse(BaseModel):
    results: list[CategorizedTransaction]
    model: str = Field(description="Modelo que produjo el resultado, para trazabilidad.")
