"""Output helpers for split results."""

from __future__ import annotations

from splitter.engine import SplitResult


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
