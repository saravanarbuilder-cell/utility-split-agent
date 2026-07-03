"""Tests for the deterministic half of the bill parser (build_parsed_bill).

No network and no API key — these exercise validation/normalization only, the
same way test_engine.py exercises the split math. The LLM extraction call
(extract_bill_fields) is a thin SDK wrapper and is not unit-tested here.
"""
from datetime import date
from decimal import Decimal

import pytest

from parser.bill_parser import ParsedBill, build_parsed_bill


def test_full_bill_parses_and_feeds_engine():
    r = build_parsed_bill({
        "amount_due": "247.86",
        "service_period_start": "2026-05-01",
        "service_period_end": "2026-05-31",
        "meter_reading": "10432",
        "notes": "",
    })
    assert r.amount == Decimal("247.86")
    assert isinstance(r.amount, Decimal)  # money is Decimal, never float
    assert r.service_period_start == date(2026, 5, 1)
    assert r.service_period_end == date(2026, 5, 31)
    assert r.meter_reading == Decimal("10432")
    assert r.service_days == 31


def test_amount_with_currency_symbol_and_commas():
    r = build_parsed_bill({
        "amount_due": "$1,247.80",
        "service_period_start": None,
        "service_period_end": None,
        "meter_reading": None,
        "notes": "",
    })
    assert r.amount == Decimal("1247.80")


def test_amount_rounds_to_cents():
    r = build_parsed_bill({"amount_due": "99.135", "service_period_start": None,
                           "service_period_end": None, "meter_reading": None, "notes": ""})
    assert r.amount == Decimal("99.14")  # ROUND_HALF_UP


def test_missing_dates_and_meter_are_optional():
    r = build_parsed_bill({
        "amount_due": "50.00",
        "service_period_start": None,
        "service_period_end": None,
        "meter_reading": None,
        "notes": "no meter on this bill",
    })
    assert r.service_period_start is None
    assert r.service_period_end is None
    assert r.meter_reading is None
    assert r.service_days is None
    assert r.notes == "no meter on this bill"


def test_missing_amount_rejected():
    with pytest.raises(ValueError, match="missing an amount"):
        build_parsed_bill({"amount_due": None, "service_period_start": None,
                           "service_period_end": None, "meter_reading": None, "notes": ""})


def test_zero_and_negative_amount_rejected():
    for bad in ("0.00", "-5.00"):
        with pytest.raises(ValueError, match="must be positive"):
            build_parsed_bill({"amount_due": bad, "service_period_start": None,
                               "service_period_end": None, "meter_reading": None, "notes": ""})


def test_unparseable_amount_rejected():
    with pytest.raises(ValueError, match="could not parse"):
        build_parsed_bill({"amount_due": "pay online", "service_period_start": None,
                           "service_period_end": None, "meter_reading": None, "notes": ""})


def test_end_before_start_rejected():
    with pytest.raises(ValueError, match="before it starts"):
        build_parsed_bill({
            "amount_due": "10.00",
            "service_period_start": "2026-05-31",
            "service_period_end": "2026-05-01",
            "meter_reading": None,
            "notes": "",
        })


def test_bad_date_format_rejected():
    with pytest.raises(ValueError, match="not an ISO"):
        build_parsed_bill({
            "amount_due": "10.00",
            "service_period_start": "05/01/2026",
            "service_period_end": None,
            "meter_reading": None,
            "notes": "",
        })


def test_negative_meter_reading_rejected():
    with pytest.raises(ValueError, match="cannot be negative"):
        build_parsed_bill({
            "amount_due": "10.00",
            "service_period_start": None,
            "service_period_end": None,
            "meter_reading": "-3",
            "notes": "",
        })


def test_parsed_bill_amount_flows_into_split_bill():
    """The parser's amount is exactly what the split engine consumes as `total`."""
    from splitter.engine import split_bill

    bill = build_parsed_bill({"amount_due": "200.00", "service_period_start": None,
                              "service_period_end": None, "meter_reading": None, "notes": ""})
    cfg = {"method": "equal", "units": [
        {"unit": "A", "tenant": "T1"}, {"unit": "B", "tenant": "T2"},
    ]}
    result = split_bill(bill.amount, cfg)
    assert sum(c.amount for c in result.charges) == Decimal("200.00")
