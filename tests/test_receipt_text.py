from datetime import date
from decimal import Decimal

import pytest

from app.domain.enums import Currency, PaymentMethod
from app.services.receipt_text import detect_currency, detect_payment_method, parse_amount, parse_date


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("$ 1.250,50", Decimal("1250.50")),
        ("TOTAL $1.250", Decimal("1250.00")),
        ("1,250.50", Decimal("1250.50")),
        ("12.50", Decimal("12.50")),
        ("12,5", Decimal("12.50")),
        ("$ 73.456,92", Decimal("73456.92")),
        ("1.234.567", Decimal("1234567.00")),
        ("3500", Decimal("3500.00")),
        ("-890,00", Decimal("890.00")),
    ],
)
def test_interpreta_importes_con_formato_argentino_e_internacional(text: str, expected: Decimal) -> None:
    assert parse_amount(text) == expected


@pytest.mark.parametrize("text", [None, "", "TOTAL", "$ 0,00"])
def test_sin_un_importe_positivo_no_hay_monto(text: str | None) -> None:
    assert parse_amount(text) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("14/10/2026", date(2026, 10, 14)),
        ("14-10-26 13:45", date(2026, 10, 14)),
        ("1.9.2026", date(2026, 9, 1)),
        ("2026-10-14", date(2026, 10, 14)),
        ("14 de octubre de 2026", date(2026, 10, 14)),
        ("14 OCT 2026", date(2026, 10, 14)),
        ("3 dic. 25", date(2025, 12, 3)),
    ],
)
def test_interpreta_fechas_con_el_dia_primero(text: str, expected: date) -> None:
    assert parse_date(text) == expected


@pytest.mark.parametrize("text", [None, "", "31/02/2026", "sin fecha"])
def test_una_fecha_ilegible_o_inexistente_no_se_inventa(text: str | None) -> None:
    assert parse_date(text) is None


@pytest.mark.parametrize(
    ("texts", "expected"),
    [
        (["TOTAL U$S 45,00"], Currency.USD),
        (["TOTAL USD 45"], Currency.USD),
        (["Total € 30"], Currency.EUR),
        (["TOTAL R$ 120,00"], Currency.BRL),
        (["TOTAL $ 1.250,50"], Currency.ARS),
    ],
)
def test_detecta_la_moneda_y_si_no_dice_ninguna_usa_la_por_defecto(
    texts: list[str], expected: Currency
) -> None:
    assert detect_currency(texts, Currency.ARS) is expected


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        (["TARJETA DE DÉBITO"], PaymentMethod.DEBIT_CARD),
        (["VISA DEBITO ****1234"], PaymentMethod.DEBIT_CARD),
        (["VISA 3 CUOTAS"], PaymentMethod.CREDIT_CARD),
        (["Pago con QR Mercado Pago"], PaymentMethod.DIGITAL_WALLET),
        (["TRANSFERENCIA BANCARIA"], PaymentMethod.BANK_TRANSFER),
        (["SU PAGO EFECTIVO"], PaymentMethod.CASH),
        (["GRACIAS POR SU COMPRA"], None),
    ],
)
def test_detecta_el_medio_de_pago_solo_si_el_comprobante_lo_dice(
    lines: list[str], expected: PaymentMethod | None
) -> None:
    assert detect_payment_method(lines) is expected
