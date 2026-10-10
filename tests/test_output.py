import csv
from decimal import Decimal
from io import StringIO

from splitter.engine import SplitResult, UnitCharge, split_bill
from splitter.output import format_split_csv, format_split_table, split_result_payload


def test_format_split_table_matches_cli_columns():
    result = split_bill(
        "247.86",
        {
            "method": "fixed_percent",
            "units": [
                {"unit": "A", "tenant": "Tenant One", "percent": 40},
                {"unit": "B", "tenant": "Tenant Two", "percent": 35},
                {"unit": "C", "tenant": "Tenant Three", "percent": 25},
            ],
        },
    )

    table = format_split_table(result)

    assert "Method: fixed_percent   Total: $247.86" in table
    assert "Unit  Tenant          Weight          Owes" in table
    assert "A     Tenant One      40        $    99.14" in table


def test_split_result_payload_is_json_ready():
    result = split_bill(
        "100.00",
        {
            "method": "equal",
            "units": [
                {"unit": "A", "tenant": "Tenant One"},
                {"unit": "B", "tenant": "Tenant Two"},
            ],
        },
    )

    payload = split_result_payload(result, "config/tenants.example.yaml")

    assert payload == {
        "method": "equal",
        "total": "100.00",
        "remainder_applied_to": None,
        "charges": [
            {"unit": "A", "tenant": "Tenant One", "amount": "50.00", "weight": "1"},
            {"unit": "B", "tenant": "Tenant Two", "amount": "50.00", "weight": "1"},
        ],
        "config_path": "config/tenants.example.yaml",
    }


def test_format_split_csv_escapes_spreadsheet_formulas():
    result = SplitResult(
        method="equal",
        total=Decimal("600.00"),
        charges=[
            UnitCharge("=1+1", "+SUM(A:A)", Decimal("100.00"), Decimal("1")),
            UnitCharge("-1+1", "@cmd", Decimal("100.00"), Decimal("1")),
            UnitCharge("\t=1+1", "\r=1+1", Decimal("100.00"), Decimal("1")),
            UnitCharge("\n=1+1", "  =SUM(A:A)", Decimal("100.00"), Decimal("1")),
            UnitCharge(" B", "Tenant Five", Decimal("100.00"), Decimal("1")),
            UnitCharge("C", "Tenant Six", Decimal("100.00"), Decimal("1")),
        ],
        remainder_applied_to=None,
    )

    csv_text = format_split_csv(result)

    assert list(csv.reader(StringIO(csv_text))) == [
        ["unit", "tenant", "weight", "amount"],
        ["'=1+1", "'+SUM(A:A)", "1", "100.00"],
        ["'-1+1", "'@cmd", "1", "100.00"],
        ["'\t=1+1", "'\r=1+1", "1", "100.00"],
        ["'\n=1+1", "'  =SUM(A:A)", "1", "100.00"],
        [" B", "Tenant Five", "1", "100.00"],
        ["C", "Tenant Six", "1", "100.00"],
    ]
