from decimal import Decimal

import pytest

from splitter.engine import split_bill


def test_equal_split_reconciles_to_total():
    cfg = {"method": "equal", "units": [
        {"unit": "A", "tenant": "T1"},
        {"unit": "B", "tenant": "T2"},
        {"unit": "C", "tenant": "T3"},
    ]}
    r = split_bill("100.00", cfg)
    assert sum(c.amount for c in r.charges) == Decimal("100.00")
    # 100/3 = 33.33 each, one unit absorbs the extra penny
    amounts = sorted(str(c.amount) for c in r.charges)
    assert amounts == ["33.33", "33.33", "33.34"]


def test_fixed_percent_exact():
    cfg = {"method": "fixed_percent", "units": [
        {"unit": "A", "tenant": "T1", "percent": 40},
        {"unit": "B", "tenant": "T2", "percent": 35},
        {"unit": "C", "tenant": "T3", "percent": 25},
    ]}
    r = split_bill("200.00", cfg)
    by_unit = {c.unit: c.amount for c in r.charges}
    assert by_unit["A"] == Decimal("80.00")
    assert by_unit["B"] == Decimal("70.00")
    assert by_unit["C"] == Decimal("50.00")
    assert sum(r.charges[i].amount for i in range(3)) == Decimal("200.00")


def test_fixed_percent_rejects_bad_sum():
    cfg = {"method": "fixed_percent", "units": [
        {"unit": "A", "tenant": "T1", "percent": 40},
        {"unit": "B", "tenant": "T2", "percent": 40},
    ]}
    with pytest.raises(ValueError, match="sum to 100"):
        split_bill("100.00", cfg)


def test_weighted_method_rejects_missing_weight():
    cfg = {"method": "occupancy", "units": [
        {"unit": "A", "tenant": "T1", "occupants": 2},
        {"unit": "B", "tenant": "T2"},
    ]}

    with pytest.raises(ValueError, match="missing 'occupants'"):
        split_bill("100.00", cfg)


def test_weighted_method_rejects_zero_total_weight():
    cfg = {"method": "square_footage", "units": [
        {"unit": "A", "tenant": "T1", "sqft": 0},
        {"unit": "B", "tenant": "T2", "sqft": 0},
    ]}

    with pytest.raises(ValueError, match="Weights sum to zero"):
        split_bill("100.00", cfg)


def test_fixed_share_normalizes():
    cfg = {"method": "fixed_share", "units": [
        {"unit": "A", "tenant": "T1", "share": 2},
        {"unit": "B", "tenant": "T2", "share": 1},
        {"unit": "C", "tenant": "T3", "share": 1},
    ]}
    r = split_bill("100.00", cfg)
    by_unit = {c.unit: c.amount for c in r.charges}
    assert by_unit["A"] == Decimal("50.00")
    assert by_unit["B"] == Decimal("25.00")
    assert by_unit["C"] == Decimal("25.00")


def test_occupancy_weighting():
    cfg = {"method": "occupancy", "units": [
        {"unit": "A", "tenant": "T1", "occupants": 3},
        {"unit": "B", "tenant": "T2", "occupants": 1},
    ]}
    r = split_bill("120.00", cfg)
    by_unit = {c.unit: c.amount for c in r.charges}
    assert by_unit["A"] == Decimal("90.00")
    assert by_unit["B"] == Decimal("30.00")


def test_square_footage_weighting_reconciles():
    cfg = {"method": "square_footage", "units": [
        {"unit": "A", "tenant": "T1", "sqft": 900},
        {"unit": "B", "tenant": "T2", "sqft": 600},
        {"unit": "C", "tenant": "T3", "sqft": 500},
    ]}
    r = split_bill("87.53", cfg)
    assert sum(c.amount for c in r.charges) == Decimal("87.53")


def test_unknown_method_rejected():
    with pytest.raises(ValueError, match="Unknown method"):
        split_bill("10.00", {"method": "vibes", "units": [{"unit": "A"}]})
