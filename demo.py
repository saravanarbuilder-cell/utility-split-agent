"""Demo: run the split engine end-to-end with synthetic data. No credentials needed.

    python demo.py
"""
import yaml
from splitter.engine import split_bill

DEMO_CONFIG = yaml.safe_load(open("config/tenants.example.yaml"))
DEMO_BILL_TOTAL = "247.86"  # fake water bill

if __name__ == "__main__":
    result = split_bill(DEMO_BILL_TOTAL, DEMO_CONFIG)
    print(f"\nMethod: {result.method}   Total: ${result.total}\n")
    print(f"{'Unit':<6}{'Tenant':<16}{'Weight':<10}{'Owes':>10}")
    print("-" * 42)
    for row in result.as_rows():
        print(f"{row['unit']:<6}{row['tenant']:<16}{row['weight']:<10}${row['amount']:>9}")
    if result.remainder_applied_to:
        print(f"\n(rounding remainder applied to unit {result.remainder_applied_to})")
    print()
