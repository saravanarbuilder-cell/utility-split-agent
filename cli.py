"""Fetch/parse a utility bill and split it across tenants — end to end.

    python cli.py bills/may_water.pdf                 # parse a local PDF, then split
    python cli.py --fetch example                     # download from a provider, parse, split
    python cli.py --amount 247.86                     # skip the LLM; split a known total
    python cli.py --list-providers                    # show registered fetchers

--fetch downloads the latest bill (needs the provider's login in .env), then
parses it. The PDF path uses the LLM parser (needs ANTHROPIC_API_KEY in .env).
The --amount form does the split only and needs no credentials.
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

from splitter.engine import split_bill
from splitter.output import format_split_table, split_result_payload


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
    print(f"\n{format_split_table(result)}\n")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="cli.py",
        description="Parse a utility bill PDF and split it across tenants.",
    )
    p.add_argument("pdf", nargs="?", help="path to the bill PDF (parsed via the LLM)")
    p.add_argument("--fetch", metavar="PROVIDER", help="download the latest bill from a provider, then parse it")
    p.add_argument("--amount", help="split this total instead of parsing a PDF (no credentials needed)")
    p.add_argument("--config", help="tenant config YAML (default: config/tenants.yaml, else the example)")
    p.add_argument("--model", default="claude-opus-4-8", help="model for PDF extraction")
    p.add_argument("--download-dir", default="downloads", help="where fetched bills are saved (default: downloads/)")
    p.add_argument("--headful", action="store_true", help="show the browser during --fetch (default: headless)")
    p.add_argument("--json", action="store_true", help="print split results as JSON instead of a table")
    p.add_argument("--list-providers", action="store_true", help="list registered fetchers and exit")
    args = p.parse_args(argv)

    if args.list_providers:
        from fetchers import available

        print("Available providers:", ", ".join(available()) or "(none)")
        return 0

    sources = [bool(args.pdf), bool(args.fetch), bool(args.amount)]
    if sum(sources) != 1:
        p.error("provide exactly one of: a PDF path, --fetch PROVIDER, or --amount")

    config_path = _resolve_config(args.config)
    if not config_path.exists():
        print(f"error: config not found: {config_path}", file=sys.stderr)
        return 2
    config = yaml.safe_load(config_path.read_text())
    if not args.json:
        print(f"Config: {config_path}")

    if args.amount:
        total = args.amount
    else:
        if args.fetch:
            # Fetch the latest bill from the provider portal (needs login in .env).
            from fetchers import get_fetcher_class

            try:
                fetcher = get_fetcher_class(args.fetch).from_env(
                    download_dir=args.download_dir, headless=not args.headful
                )
                if not args.json:
                    print(f"Fetching latest bill from '{args.fetch}'...")
                pdf_path = fetcher.fetch_latest_bill()
                if not args.json:
                    print(f"Downloaded: {pdf_path}")
            except (KeyError, ValueError) as e:  # unknown provider / missing creds
                print(f"error: {e}", file=sys.stderr)
                return 2
            except Exception as e:  # browser/login/download failure
                print(f"error: could not fetch bill: {e}", file=sys.stderr)
                return 1
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
        if not args.json:
            _print_bill(bill)
        total = bill.amount

    try:
        result = split_bill(total, config)
    except ValueError as e:
        print(f"error: could not split bill: {e}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(split_result_payload(result, str(config_path)), indent=2))
    else:
        _print_split(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
