"""Tipos del dominio de IA.

OJO con el limite: aca van solo los tipos que esta API necesita para razonar
(que categorias existe, que nivel de confianza hay). Las reglas de negocio
financiero -- metas, presupuestos, permisos -- viven en FinGrow.Domain, del
lado .NET. Si una regla aparece escrita de los dos lados, se van a
desincronizar.
"""

from enum import StrEnum


class ExpenseCategory(StrEnum):
    """Categorias de gasto que el modelo puede asignar.

    Tiene que estar alineada con el enum equivalente de FinGrow.Domain/Enums.
    """

    ALIMENTOS = "alimentos"
    TRANSPORTE = "transporte"
    VIVIENDA = "vivienda"
    SERVICIOS = "servicios"
    SALUD = "salud"
    EDUCACION = "educacion"
    ENTRETENIMIENTO = "entretenimiento"
    INDUMENTARIA = "indumentaria"
    AHORRO_INVERSION = "ahorro_inversion"
    OTROS = "otros"


class IncomeCategory(StrEnum):
    SALARIO = "salario"
    FREELANCE = "freelance"
    INVERSIONES = "inversiones"
    REGALO = "regalo"
    OTROS = "otros"


class TransactionType(StrEnum):
    EXPENSE = "expense"
    INCOME = "income"


class PaymentMethod(StrEnum):
    CASH = "cash"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    DIGITAL_WALLET = "digital_wallet"


class Currency(StrEnum):
    ARS = "ARS"
    USD = "USD"
    EUR = "EUR"
    BRL = "BRL"


class AudioFormat(StrEnum):
    OGG = "ogg"
    MP3 = "mp3"
    MP4 = "mp4"
    M4A = "m4a"
    WAV = "wav"
    WEBM = "webm"
    FLAC = "flac"


class DocumentFormat(StrEnum):
    JPEG = "jpeg"
    PNG = "png"
    PDF = "pdf"
