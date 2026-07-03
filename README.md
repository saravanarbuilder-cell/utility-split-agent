# Utility Split Agent

Config-driven tool that splits shared utility bills (water, etc.) across rental
tenants using a chosen allocation method, with money-safe arithmetic and an
auditable rounding trail.

Design principle: **deterministic work is code, judgment is the LLM.** The split
math is pure, tested Python. An LLM is used only for the fuzzy step — reading a
messy bill PDF into structured fields.

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

## Status

- [x] Split engine (5 methods, tested)
- [x] Demo mode with synthetic data
- [x] Bill parser (LLM: PDF → amount / period / meter reading; validation tested)
- [ ] Provider fetchers (Playwright, one module per provider)

## License

MIT — see [LICENSE](LICENSE).
