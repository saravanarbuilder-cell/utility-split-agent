"""Config-driven utility bill split engine.

The engine knows nothing about your real tenants, percentages, or providers.
All of that lives in a YAML config supplied at runtime. This module only
implements the *shapes* of splits and the money-safe arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


SUPPORTED_METHODS = {
    "equal",           # total / number of units
    "fixed_percent",   # each unit has a percent; must sum to 100
    "fixed_share",     # weighted shares (e.g. 2:1:1); engine normalizes
    "occupancy",       # weighted by occupants per unit (RUBS-style)
    "square_footage",  # weighted by area per unit
}

# Which per-unit weight field each method reads.
_WEIGHT_FIELD = {
    "fixed_percent": "percent",
    "fixed_share": "share",
    "occupancy": "occupants",
    "square_footage": "sqft",
}


@dataclass
class UnitCharge:
    unit: str
    tenant: str
    amount: Decimal   # rounded to cents
    weight: Decimal   # the raw weight used (for the audit trail)


@dataclass
class SplitResult:
    method: str
    total: Decimal
    charges: list[UnitCharge]
    remainder_applied_to: str | None  # unit that absorbed the rounding penny(s)

    def as_rows(self) -> list[dict]:
        return [
            {
                "unit": c.unit,
                "tenant": c.tenant,
                "amount": f"{c.amount:.2f}",
                "weight": f"{c.weight:g}",
            }
            for c in self.charges
        ]


def _money(x) -> Decimal:
    try:
        value = Decimal(str(x))
    except (InvalidOperation, ValueError) as e:
        raise ValueError(f"Bill total must be a valid number, got {x!r}.") from e
    if not value.is_finite():
        raise ValueError(f"Bill total must be a finite number, got {x!r}.")
    try:
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation as e:
        raise ValueError(f"Bill total must be a valid cents amount, got {x!r}.") from e


def _weight(value, *, unit: str | None, field: str) -> Decimal:
    try:
        weight = Decimal(str(value))
    except (InvalidOperation, ValueError) as e:
        raise ValueError(f"Unit {unit!r} has invalid {field}: {value!r}.") from e
    if not weight.is_finite():
        raise ValueError(f"Unit {unit!r} has invalid {field}: {value!r}.")
    if weight < 0:
        raise ValueError(f"Unit {unit!r} has negative {field}.")
    return weight


def _required_label(unit: dict, field: str) -> str:
    value = unit.get(field)
    label = str(value).strip() if value is not None else ""
    if not label:
        raise ValueError(f"Each config unit must have a non-empty {field}.")
    return label


def split_bill(total, config: dict) -> SplitResult:
    """Split `total` across the units defined in `config`.

    config schema (all example values, no real data):
        method: equal | fixed_percent | fixed_share | occupancy | square_footage
        units:
          - unit: "A"
            tenant: "Tenant 1"
            percent: 40        # only for fixed_percent
            share: 2           # only for fixed_share
            occupants: 3       # only for occupancy
            sqft: 900          # only for square_footage
    """
    method = config.get("method")
    if method not in SUPPORTED_METHODS:
        raise ValueError(
            f"Unknown method {method!r}. Supported: {sorted(SUPPORTED_METHODS)}"
        )

    units = config.get("units") or []
    if not units:
        raise ValueError("Config has no units.")
    if not isinstance(units, list):
        raise ValueError("Config units must be a list of unit mappings.")
    if not all(isinstance(unit, dict) for unit in units):
        raise ValueError("Each config unit must be a mapping.")
    unit_names = [_required_label(unit, "unit") for unit in units]
    tenant_names = [_required_label(unit, "tenant") for unit in units]
    duplicate_units = sorted({name for name in unit_names if unit_names.count(name) > 1})
    if duplicate_units:
        raise ValueError(f"Duplicate unit identifiers are not allowed: {duplicate_units}.")

    total = _money(total)
    if total <= 0:
        raise ValueError("Bill total must be positive.")

    # 1. Determine each unit's raw weight.
    if method == "equal":
        weights = [Decimal(1) for _ in units]
    else:
        field = _WEIGHT_FIELD[method]
        weights = []
        for u in units:
            unit = u.get("unit")
            if field not in u:
                raise ValueError(f"Unit {unit!r} missing '{field}' for method '{method}'.")
            weights.append(_weight(u[field], unit=unit, field=field))

    if method == "fixed_percent":
        pct_sum = sum(weights)
        if pct_sum != Decimal(100):
            raise ValueError(f"fixed_percent weights must sum to 100, got {pct_sum}.")

    weight_sum = sum(weights)
    if weight_sum == 0:
        raise ValueError("Weights sum to zero; cannot split.")

    # 2. Compute each share, rounded to cents.
    charges: list[UnitCharge] = []
    for unit_name, tenant_name, w in zip(unit_names, tenant_names, weights):
        raw = total * (w / weight_sum)
        charges.append(
            UnitCharge(
                unit=unit_name,
                tenant=tenant_name,
                amount=_money(raw),
                weight=w,
            )
        )

    # 3. Reconcile rounding so the parts sum EXACTLY to the total.
    allocated = sum(c.amount for c in charges)
    remainder = total - allocated
    remainder_unit = None
    if remainder != 0:
        # Put the leftover penny/pennies on the largest-share unit.
        target = max(charges, key=lambda c: c.amount)
        target.amount = _money(target.amount + remainder)
        remainder_unit = target.unit

    return SplitResult(
        method=method,
        total=total,
        charges=charges,
        remainder_applied_to=remainder_unit,
    )
