"""Output helpers for split results."""

from __future__ import annotations

from splitter.engine import SplitResult


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
