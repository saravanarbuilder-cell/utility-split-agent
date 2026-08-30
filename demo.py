"""Demo: run the split engine end-to-end. No credentials needed.

    python demo.py                 # uses config/tenants.yaml if present, else the example
    python demo.py 312.40          # override the bill total
"""
import sys
from pathlib import Path

import yaml

from splitter.engine import split_bill
from splitter.output import format_split_table

# Prefer your real (gitignored) config; fall back to the committed example.
CONFIG_PATH = Path("config/tenants.yaml")
if not CONFIG_PATH.exists():
    CONFIG_PATH = Path("config/tenants.example.yaml")

DEMO_BILL_TOTAL = sys.argv[1] if len(sys.argv) > 1 else "247.86"  # fake water bill

if __name__ == "__main__":
    config = yaml.safe_load(CONFIG_PATH.read_text())
    result = split_bill(DEMO_BILL_TOTAL, config)
    print(f"\nConfig: {CONFIG_PATH}")
    print(f"{format_split_table(result)}\n")
