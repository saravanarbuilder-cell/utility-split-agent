# Utility Split Agent

[![CI](https://github.com/saravanarbuilder-cell/utility-split-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/saravanarbuilder-cell/utility-split-agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Config-driven tool that splits shared utility bills (water, etc.) across rental
tenants using a chosen allocation method, with money-safe arithmetic and an
auditable rounding trail.

Design principle: **deterministic work is code, judgment is the LLM.** The split
math is pure, tested Python. An LLM is used only for the fuzzy step — reading a
messy bill PDF into structured fields.

## Architecture

Three stages, `fetch → parse → split`. The LLM touches exactly one step; every
correctness guarantee (Decimal money, date/range checks, the split math) lives in
pure Python.

```
    provider portal   (login in .env)
                           │
                           ▼
    ┌──────────────────────────────────────────────┐
    │ FETCH   fetchers/ · BaseFetcher              │
    │         Playwright, read-only                │
    │         fetch_latest_bill()  ──▶  bill.pdf   │
    └──────────────────────────────────────────────┘
                           │   bill.pdf
                           ▼
    ┌──────────────────────────────────────────────┐
    │ PARSE   parser/                              │
    │   extract_bill_fields ─▶ Claude (LLM)        │
    │                           ▲ only fuzzy step  │
    │   raw fields ─▶ build_parsed_bill            │
    │      (pure: Decimal, dates, range; tested)   │
    └──────────────────────────────────────────────┘
                           │   ParsedBill.amount  (the total)
    config/tenants.yaml ──────────▶ ▼
      (method + weights)
    ┌──────────────────────────────────────────────┐
    │ SPLIT   splitter/engine.py                   │
    │   split_bill()                               │
    │     Decimal · 5 methods · exact rounding     │
    │   ─▶ per-tenant charges  (sum == total)      │
    └──────────────────────────────────────────────┘
                           │
                           ▼
    human enters charges in Apartments.com
      (never automated — ToS + account safety)

    cli.py runs it all:  --fetch PROVIDER │ <bill.pdf> │ --amount
```

- **`code` vs `LLM`** — only `extract_bill_fields` calls Claude. Its messy output
  is immediately validated by `build_parsed_bill`, which is pure and unit-tested.
- **Read-only fetchers** — they download bills and nothing else. A human enters the
  final per-tenant charges into Apartments.com; that step is never automated.
- **Secrets** — credentials and real splits live only in `.env` / `config/tenants.yaml`
  (both gitignored); committed `*.example` files hold placeholders.

## Quick start

```bash
pip install pytest pyyaml anthropic
python demo.py        # runs an end-to-end split on synthetic data
python -m pytest -q   # test suite
```

`demo.py` and the test suite need no credentials and no real data. The `anthropic`
dependency is only used by the bill parser (below); the split engine and all tests
run without it. To parse real bills, put `ANTHROPIC_API_KEY` in `.env` (gitignored).

## Split methods

Set `method` in your config:

| method           | weight field | behavior                                  |
|------------------|--------------|-------------------------------------------|
| `equal`          | (none)       | total / number of units                   |
| `fixed_percent`  | `percent`    | fixed % per unit (must sum to 100)         |
| `fixed_share`    | `share`      | weighted shares (e.g. 2:1:1), normalized   |
| `occupancy`      | `occupants`  | weighted by occupants per unit (RUBS-style)|
| `square_footage` | `sqft`       | weighted by unit area                      |

Money is `Decimal` end-to-end; rounding remainders are reconciled so parts sum
exactly to the bill, and the absorbing unit is recorded for audit.

## Configuration & privacy

Secrets and real tenant data never live in code or version control:

- Copy `.env.example` → `.env` (gitignored) for API keys and provider logins.
- Copy `config/tenants.example.yaml` → `config/tenants.yaml` (gitignored) for
  real splits.

The committed `*.example` files contain only placeholder data.

## Bill parser

`parser/bill_parser.py` reads a messy bill PDF into structured fields
(`amount`, service period, meter reading). Following the design principle, it is
split in two:

- **`extract_bill_fields` / `parse_bill`** — the fuzzy step. Sends the PDF to
  Claude (`claude-opus-4-8`) with a constrained JSON schema and returns raw
  fields. Needs `ANTHROPIC_API_KEY`.
- **`build_parsed_bill`** — pure, tested, no network. Validates and normalizes
  the raw fields: money as `Decimal`, ISO dates, range checks (positive amount,
  end ≥ start). This is where correctness is guaranteed.

```python
from parser import parse_bill
bill = parse_bill("bills/may_water.pdf")   # -> ParsedBill
split_bill(bill.amount, config)            # amount feeds the engine as the total
```

## Provider fetchers

`fetchers/` logs into a utility portal with Playwright and downloads the latest
bill PDF. One module per provider, all behind `BaseFetcher`, which owns the
browser lifecycle and credential loading; each provider only implements `login`
and `download_latest_bill`. Fetchers are **read-only** — they download bills and
never submit charges (a human enters those; Apartments.com is never automated).

```bash
pip install playwright && python -m playwright install chromium   # one-time
```

`fetchers/example_provider.py` is a runnable template — copy it to
`fetchers/<your_provider>.py` and adjust the selectors to your portal. Credentials
come from `.env` only (`PROVIDER1_URL` / `_USERNAME` / `_PASSWORD`), never from
code or the command line.

## CLI

`cli.py` runs the whole pipeline — fetch or parse a bill, then split it:

```bash
python cli.py --fetch example                      # download from a provider, parse, split
python cli.py bills/may_water.pdf                  # parse a local PDF (needs API key), then split
python cli.py bills/may_water.pdf --config config/tenants.yaml
python cli.py --amount 247.86                      # skip the LLM; split a known total (no key)
python cli.py --list-providers                     # show registered fetchers
```

It resolves the config the same way `demo.py` does (prefers `config/tenants.yaml`,
falls back to the example).

## Status

All stages built and tested — full pipeline runs **fetch → parse → split**.

- [x] Split engine (5 methods, Decimal money, tested)
- [x] Demo mode with synthetic data
- [x] Bill parser (LLM: PDF → amount / period / meter reading; pure validation tested)
- [x] Provider fetchers (Playwright, `BaseFetcher` + registry; example template, lifecycle tested)
- [x] CLI (`--fetch` / PDF / `--amount`, wired end to end)
- [x] End-to-end integration test (fetch → parse → split)

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the next public milestones. The near-term focus
is making the project easier to try quickly, safer to adapt to real utility
providers, and clearer as a reference architecture for agent-assisted workflows.

## License

MIT — see [LICENSE](LICENSE).
