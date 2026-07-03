# Utility Split Agent

Config-driven tool that splits shared utility bills (water, etc.) across rental
tenants using a chosen allocation method, with money-safe arithmetic and an
auditable rounding trail.

Design principle: **deterministic work is code, judgment is the LLM.** The split
math is pure, tested Python. An LLM is used only for the fuzzy step — reading a
messy bill PDF into structured fields.

## Quick start

```bash
pip install pytest pyyaml
python demo.py        # runs an end-to-end split on synthetic data
python -m pytest -q   # test suite
```

`demo.py` needs no credentials and no real data — it runs on the dummy config
in `config/tenants.example.yaml`.

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

## Status

- [x] Split engine (5 methods, tested)
- [x] Demo mode with synthetic data
- [ ] Bill parser (LLM: PDF → amount / period / meter reading)
- [ ] Provider fetchers (Playwright, one module per provider)

## License

MIT — see [LICENSE](LICENSE).
