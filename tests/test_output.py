from splitter.engine import split_bill
from splitter.output import format_split_table


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
