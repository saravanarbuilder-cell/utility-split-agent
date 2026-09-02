"""Read a messy utility-bill PDF into structured fields.

Design principle (see CLAUDE.md): **judgment is the LLM, deterministic work is code.**
An LLM only does the fuzzy step — turning a scanned/rendered bill into raw fields.
Everything that must be *correct* (money as Decimal, date sanity, range checks)
lives in `build_parsed_bill`, which is pure Python: no network, no API key, and
fully unit-testable. The Anthropic SDK is imported lazily inside the extraction
call so the validation layer and its tests never depend on it.

The extracted `amount` is the total that feeds `splitter.engine.split_bill`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

# The LLM is asked to read a utility bill and return these fields. Money and
# numeric values come back as *strings* so we never touch a float, and dates as
# ISO strings; the pure validator below converts and range-checks them.
_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "amount_due": {
            "type": "string",
            "description": (
                "Total amount due for this bill, as a plain decimal string like "
                "'247.86'. Digits and at most one decimal point only — no currency "
                "symbol, no thousands separators. If several totals appear, use the "
                "current amount due, not a past balance or an autopay estimate."
            ),
        },
        "service_period_start": {
            "anyOf": [{"type": "string"}, {"type": "null"}],
            "description": "First day of the billing/service period as YYYY-MM-DD, or null if not shown.",
        },
        "service_period_end": {
            "anyOf": [{"type": "string"}, {"type": "null"}],
            "description": "Last day of the billing/service period as YYYY-MM-DD, or null if not shown.",
        },
        "meter_reading": {
            "anyOf": [{"type": "string"}, {"type": "null"}],
            "description": (
                "Current meter reading as a plain numeric string, or null if the bill "
                "shows no meter reading. Use the current/ending read, not the prior read."
            ),
        },
        "notes": {
            "type": "string",
            "description": "Short free-text note on anything ambiguous or worth a human glance. Empty string if all clear.",
        },
    },
    "required": ["amount_due", "service_period_start", "service_period_end", "meter_reading", "notes"],
    "additionalProperties": False,
}

_SYSTEM = (
    "You extract structured data from a single utility bill (water, gas, electric, etc.). "
    "Report only what the document actually states — never guess or fabricate a value. "
    "If a field is genuinely absent, return null (or an empty string for notes). "
    "Amounts and meter readings must be plain numeric strings with no currency symbols "
    "or thousands separators; dates must be YYYY-MM-DD."
)

_MODEL = "claude-opus-4-8"


@dataclass
class ParsedBill:
    amount: Decimal                        # total due, rounded to cents — feeds split_bill
    service_period_start: date | None
    service_period_end: date | None
    meter_reading: Decimal | None
    notes: str = ""

    @property
    def service_days(self) -> int | None:
        """Length of the billing period in days (inclusive), if both dates are known."""
        if self.service_period_start is None or self.service_period_end is None:
            return None
        return (self.service_period_end - self.service_period_start).days + 1


def _money(x) -> Decimal:
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _clean_number(raw: str) -> str:
    """Strip the noise a bill (or the model) might leave on a numeric string."""
    return str(raw).strip().replace("$", "").replace(",", "").replace(" ", "")


def _parse_date(value, field: str) -> date | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError as e:
        raise ValueError(f"{field}: not an ISO (YYYY-MM-DD) date: {value!r}") from e


def build_parsed_bill(fields: dict) -> ParsedBill:
    """Validate and normalize raw extracted fields into a ParsedBill.

    Pure: no network, no SDK, no API key. This is the deterministic half of the
    parser and is where all the correctness guarantees live. Raises ValueError on
    anything that can't be a legitimate bill (missing/negative amount, unparseable
    numbers or dates, an end date before the start).
    """
    if "amount_due" not in fields or fields["amount_due"] in (None, ""):
        raise ValueError("Extracted bill is missing an amount_due.")

    raw_amount = fields["amount_due"]
    try:
        amount = Decimal(_clean_number(raw_amount))
    except InvalidOperation as e:
        raise ValueError(f"amount_due: could not parse {raw_amount!r} as a number.") from e
    if not amount.is_finite():
        raise ValueError(f"amount_due must be a finite number, got {amount}.")
    if amount <= 0:
        raise ValueError(f"amount_due must be positive, got {amount}.")
    amount = _money(amount)

    start = _parse_date(fields.get("service_period_start"), "service_period_start")
    end = _parse_date(fields.get("service_period_end"), "service_period_end")
    if start is not None and end is not None and end < start:
        raise ValueError(f"service period ends ({end}) before it starts ({start}).")

    meter = None
    raw_meter = fields.get("meter_reading")
    if raw_meter not in (None, ""):
        try:
            meter = Decimal(_clean_number(raw_meter))
        except InvalidOperation as e:
            raise ValueError(f"meter_reading: could not parse {raw_meter!r} as a number.") from e
        if not meter.is_finite():
            raise ValueError(f"meter_reading must be finite, got {meter}.")
        if meter < 0:
            raise ValueError(f"meter_reading cannot be negative, got {meter}.")

    return ParsedBill(
        amount=amount,
        service_period_start=start,
        service_period_end=end,
        meter_reading=meter,
        notes=str(fields.get("notes", "") or ""),
    )


def extract_bill_fields(pdf_bytes: bytes, *, client=None, model: str = _MODEL) -> dict:
    """Fuzzy step: send the bill PDF to Claude and get back raw extracted fields.

    Returns the raw dict (matching `_EXTRACTION_SCHEMA`) — pass it to
    `build_parsed_bill` for validation. Requires ANTHROPIC_API_KEY in the
    environment (put it in .env, which is gitignored). The SDK is imported here,
    lazily, so importing this module doesn't require the SDK or a key.
    """
    import base64
    import json

    import anthropic

    client = client or anthropic.Anthropic()
    b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=_SYSTEM,
        # Structured output constrains the reply to our schema; low effort keeps
        # this cheap — extraction is not an intelligence-hard task.
        output_config={
            "format": {"type": "json_schema", "schema": _EXTRACTION_SCHEMA},
            "effort": "low",
        },
        messages=[
            {
                "role": "user",
                "content": [
                    # Document block goes before the text instruction.
                    {
                        "type": "document",
                        "source": {"type": "base64", "media_type": "application/pdf", "data": b64},
                    },
                    {"type": "text", "text": "Extract the billing fields from this utility bill."},
                ],
            }
        ],
    )

    text = next(block.text for block in response.content if block.type == "text")
    return json.loads(text)


def parse_bill(pdf_path, *, client=None, model: str = _MODEL) -> ParsedBill:
    """Read a bill PDF from disk and return a validated ParsedBill."""
    from pathlib import Path

    raw = extract_bill_fields(Path(pdf_path).read_bytes(), client=client, model=model)
    return build_parsed_bill(raw)
