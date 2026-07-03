"""Parse a utility bill PDF and split it across tenants — end to end.

    python cli.py bills/may_water.pdf                 # parse PDF, then split
    python cli.py bills/may_water.pdf --config config/tenants.yaml
    python cli.py --amount 247.86                     # skip the LLM; split a known total

The PDF path uses the LLM parser (needs ANTHROPIC_API_KEY in .env). The
--amount form does the split only and needs no credentials.
"""
import argparse
import sys
from pathlib import Path

import yaml

from splitter.engine import split_bill


def _resolve_config(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    # Prefer your real (gitignored) config; fall back to the committed example.
    real = Path("config/tenants.yaml")
    return real if real.exists() else Path("config/tenants.example.yaml")


def _print_bill(bill) -> None:
    print("\nParsed bill")
    print(f"  amount:        ${bill.amount}")
    period = "—"
    if bill.service_period_start or bill.service_period_end:
        period = f"{bill.service_period_start or '?'} → {bill.service_period_end or '?'}"
        if bill.service_days is not None:
            period += f"  ({bill.service_days} days)"
    print(f"  service period: {period}")
    print(f"  meter reading:  {bill.meter_reading if bill.meter_reading is not None else '—'}")
    if bill.notes:
        print(f"  notes:          {bill.notes}")


def _print_split(result) -> None:
    print(f"\nMethod: {result.method}   Total: ${result.total}\n")
    print(f"{'Unit':<6}{'Tenant':<16}{'Weight':<10}{'Owes':>10}")
    print("-" * 42)
    for row in result.as_rows():
        print(f"{row['unit']:<6}{row['tenant']:<16}{row['weight']:<10}${row['amount']:>9}")
    if result.remainder_applied_to:
        print(f"\n(rounding remainder applied to unit {result.remainder_applied_to})")
    print()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="cli.py",
        description="Parse a utility bill PDF and split it across tenants.",
    )
    p.add_argument("pdf", nargs="?", help="path to the bill PDF (parsed via the LLM)")
    p.add_argument("--amount", help="split this total instead of parsing a PDF (no credentials needed)")
    p.add_argument("--config", help="tenant config YAML (default: config/tenants.yaml, else the example)")
    p.add_argument("--model", default="claude-opus-4-8", help="model for PDF extraction")
    args = p.parse_args(argv)

    if not args.pdf and not args.amount:
        p.error("provide a PDF path, or --amount to split a known total")
    if args.pdf and args.amount:
        p.error("provide either a PDF path or --amount, not both")

    config_path = _resolve_config(args.config)
    if not config_path.exists():
        print(f"error: config not found: {config_path}", file=sys.stderr)
        return 2
    config = yaml.safe_load(config_path.read_text())
    print(f"Config: {config_path}")

    if args.amount:
        total = args.amount
    else:
        pdf_path = Path(args.pdf)
        if not pdf_path.exists():
            print(f"error: PDF not found: {pdf_path}", file=sys.stderr)
            return 2
        # Imported lazily so --amount and --help don't require the anthropic SDK.
        from parser import parse_bill

        try:
            bill = parse_bill(pdf_path, model=args.model)
        except Exception as e:  # SDK/auth/network errors or validation ValueError
            print(f"error: could not parse bill: {e}", file=sys.stderr)
            return 1
        _print_bill(bill)
        total = bill.amount

    try:
        result = split_bill(total, config)
    except ValueError as e:
        print(f"error: could not split bill: {e}", file=sys.stderr)
        return 1
    _print_split(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
