"""Output helpers for split results."""

from __future__ import annotations

import csv
from io import StringIO

from splitter.engine import SplitResult


_SPREADSHEET_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n")


def _escape_spreadsheet_cell(value: str) -> str:
    """Prevent spreadsheet apps from evaluating exported labels as formulas."""
    text = str(value)
    if text and text.lstrip().startswith(_SPREADSHEET_FORMULA_PREFIXES):
        return f"'{text}"
    return text


def split_result_payload(result: SplitResult, config_path: str | None = None) -> dict:
    """Return a JSON-serializable split result payload."""
    payload = {
        "method": result.method,
        "total": f"{result.total:.2f}",
        "remainder_applied_to": result.remainder_applied_to,
        "charges": result.as_rows(),
    }
    if config_path is not None:
        payload["config_path"] = config_path
    return payload


def format_split_table(result: SplitResult) -> str:
    """Return the human-readable split table used by CLI and demo output."""
    lines = [
        f"Method: {result.method}   Total: ${result.total}",
        "",
        f"{'Unit':<6}{'Tenant':<16}{'Weight':<10}{'Owes':>10}",
        "-" * 42,
    ]
    for row in result.as_rows():
        lines.append(
            f"{row['unit']:<6}{row['tenant']:<16}{row['weight']:<10}${row['amount']:>9}"
        )
    if result.remainder_applied_to:
        lines.extend(["", f"(rounding remainder applied to unit {result.remainder_applied_to})"])
    return "\n".join(lines)


def format_split_csv(result: SplitResult) -> str:
    """Return split results as CSV for spreadsheet import."""
    out = StringIO()
    writer = csv.DictWriter(out, fieldnames=["unit", "tenant", "weight", "amount"])
    writer.writeheader()
    for row in result.as_rows():
        writer.writerow(
            {
                **row,
                "unit": _escape_spreadsheet_cell(row["unit"]),
                "tenant": _escape_spreadsheet_cell(row["tenant"]),
            }
        )
    return out.getvalue().rstrip("\r\n")
