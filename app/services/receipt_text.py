import re
import unicodedata
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app.domain.enums import Currency, PaymentMethod

_CENTS = Decimal("0.01")
_NUMBER = re.compile(r"\d[\d.,]*\d|\d")
_NUMERIC_DATE = re.compile(r"(\d{1,4})[/\-.](\d{1,2})[/\-.](\d{1,4})")
_TEXT_DATE = re.compile(r"(\d{1,2})\s*(?:de\s+)?([a-z]{3,})\.?\s*(?:de\s+|del\s+)?(\d{2,4})")

_MONTHS = {
    "ene": 1,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "aug": 8,
    "sep": 9,
    "set": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
    "dec": 12,
}

_CURRENCY_MARKERS = (
    (Currency.USD, re.compile(r"\b(usd|us\$|u\$s|u\$d|dolares?)")),
    (Currency.EUR, re.compile(r"(\beur\b|€|\beuros?\b)")),
    (Currency.BRL, re.compile(r"(\bbrl\b|r\$|\breais\b|\breales\b)")),
)

_PAYMENT_MARKERS = (
    (PaymentMethod.DEBIT_CARD, re.compile(r"\b(debito|debit|maestro|visa electron)\b")),
    (
        PaymentMethod.CREDIT_CARD,
        re.compile(r"\b(credito|credit|cuotas?|amex|american express|mastercard|visa|naranja|cabal)\b"),
    ),
    (PaymentMethod.DIGITAL_WALLET, re.compile(r"\b(mercado ?pago|modo|qr|billetera|uala|cuenta dni)\b")),
    (PaymentMethod.BANK_TRANSFER, re.compile(r"\b(transferencia|cbu|cvu)\b")),
    (PaymentMethod.CASH, re.compile(r"\b(efectivo|contado|cash)\b")),
)


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def parse_amount(text: str | None) -> Decimal | None:
    if not text:
        return None

    numbers = _NUMBER.findall(text)
    if not numbers:
        return None

    try:
        amount = Decimal(_to_plain_number(numbers[-1])).quantize(_CENTS, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None

    return amount if amount > 0 else None


def _to_plain_number(token: str) -> str:
    last_dot = token.rfind(".")
    last_comma = token.rfind(",")

    if last_dot >= 0 and last_comma >= 0:
        decimal_separator = "." if last_dot > last_comma else ","
        thousands_separator = "," if decimal_separator == "." else "."
        return token.replace(thousands_separator, "").replace(decimal_separator, ".")

    separator = "." if last_dot >= 0 else "," if last_comma >= 0 else None
    if separator is None:
        return token

    integer, _, decimals = token.rpartition(separator)
    if token.count(separator) == 1 and len(decimals) in (1, 2):
        return f"{integer}.{decimals}"

    return token.replace(separator, "")


def parse_date(text: str | None) -> date | None:
    if not text:
        return None

    normalized = normalize(text)

    numeric = _NUMERIC_DATE.search(normalized)
    if numeric:
        first, second, third = numeric.groups()
        if len(first) == 4:
            return _safe_date(int(first), int(second), int(third))
        return _safe_date(_full_year(third), int(second), int(first))

    textual = _TEXT_DATE.search(normalized)
    if textual:
        day, month_name, year = textual.groups()
        month = _MONTHS.get(month_name[:3])
        if month is not None:
            return _safe_date(_full_year(year), month, int(day))

    return None


def _full_year(year: str) -> int:
    value = int(year)
    return 2000 + value if len(year) <= 2 else value


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def detect_currency(texts: list[str], default: Currency) -> Currency:
    joined = normalize(" ".join(texts))
    for currency, pattern in _CURRENCY_MARKERS:
        if pattern.search(joined):
            return currency

    return default


def detect_payment_method(lines: list[str]) -> PaymentMethod | None:
    joined = normalize(" ".join(lines))
    for payment_method, pattern in _PAYMENT_MARKERS:
        if pattern.search(joined):
            return payment_method

    return None
