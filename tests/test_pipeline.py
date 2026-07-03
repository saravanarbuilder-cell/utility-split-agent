"""End-to-end pipeline test: fetch -> parse -> split.

Exercises the real code path across all three stages. The only stubbed piece is
the network call to Claude: `parse_bill` accepts a `client`, so we inject a fake
Anthropic client that returns canned extraction fields. Everything else is real —
the fetcher drives an actual browser against a local portal, `parse_bill` reads
the downloaded bytes and runs the real validation, and `split_bill` does the math.

Skips when the chromium binary isn't installed (see conftest.py).
"""
import base64
import json
from decimal import Decimal

from fetchers.base import ProviderCredentials
from fetchers.example_provider import ExampleProviderFetcher
from parser import parse_bill
from splitter.engine import split_bill


class _FakeAnthropicClient:
    """Stand-in for anthropic.Anthropic that returns fixed extraction JSON.

    Records the PDF bytes it was handed so the test can assert the fetched file
    actually reached the parser.
    """

    def __init__(self, fields: dict):
        self._fields = fields
        self.received_pdf: bytes | None = None
        self.messages = self._Messages(self)

    class _Messages:
        def __init__(self, parent):
            self._parent = parent

        def create(self, **kwargs):
            doc = kwargs["messages"][0]["content"][0]
            self._parent.received_pdf = base64.b64decode(doc["source"]["data"])
            text = json.dumps(self._parent._fields)
            block = type("Block", (), {"type": "text", "text": text})()
            return type("Response", (), {"content": [block]})()


def test_fetch_parse_split(tmp_path, fake_portal, require_chromium):
    # 1. FETCH — real browser logs into the local portal and downloads the PDF.
    creds = ProviderCredentials(url=fake_portal, username="u", password="p")
    fetcher = ExampleProviderFetcher(creds, download_dir=tmp_path / "downloads", headless=True)
    pdf_path = fetcher.fetch_latest_bill()
    assert pdf_path.exists()

    # 2. PARSE — real parse_bill with the LLM call stubbed via the client seam.
    fake = _FakeAnthropicClient({
        "amount_due": "247.86",
        "service_period_start": "2026-05-01",
        "service_period_end": "2026-05-31",
        "meter_reading": "10432",
        "notes": "",
    })
    bill = parse_bill(pdf_path, client=fake)

    # The fetched bytes actually flowed into the parser.
    assert fake.received_pdf is not None and fake.received_pdf.startswith(b"%PDF")
    assert bill.amount == Decimal("247.86")
    assert bill.service_days == 31

    # 3. SPLIT — real engine; parts reconcile exactly to the parsed total.
    config = {"method": "fixed_percent", "units": [
        {"unit": "A", "tenant": "T1", "percent": 40},
        {"unit": "B", "tenant": "T2", "percent": 35},
        {"unit": "C", "tenant": "T3", "percent": 25},
    ]}
    result = split_bill(bill.amount, config)
    assert sum(c.amount for c in result.charges) == Decimal("247.86")
    assert {c.unit: c.amount for c in result.charges}["A"] == Decimal("99.14")
