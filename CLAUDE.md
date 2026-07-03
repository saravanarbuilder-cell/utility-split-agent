# Utility Split Agent

Config-driven RUBS-style utility bill splitter for rental properties.

## Architecture
- code does deterministic work, Claude does judgment (parsing messy bills)
- splitter/engine.py: pure-Python split engine, Decimal money, 5 methods. TESTED.
- fetchers (TODO): Playwright, one module per provider, BaseFetcher interface
- parser (TODO): Claude reads bill PDF -> {amount, service_period, meter_reading}

## Hard rules
- Never auto-write to Apartments.com (ToS + account risk). Human enters charges.
- Secrets only in .env (gitignored). Real splits in config/tenants.yaml (gitignored).
- Money is always Decimal, never float.
