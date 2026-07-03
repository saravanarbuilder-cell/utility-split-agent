"""Tests for the provider fetcher framework.

The credential + registry tests are pure (no Playwright, no browser, no network).
The integration test drives the real `example` fetcher against a locally served
fake portal; it skips automatically if Playwright's browser binary isn't installed
(`playwright install chromium`), so the default suite stays green everywhere.
"""
import functools
import http.server
import threading
from pathlib import Path

import pytest

from fetchers import available, get_fetcher_class
from fetchers.base import BaseFetcher, ProviderCredentials
from fetchers.example_provider import ExampleProviderFetcher


# --- credentials -------------------------------------------------------------

def test_credentials_from_env():
    env = {"PROVIDER1_URL": "https://x/login", "PROVIDER1_USERNAME": "u", "PROVIDER1_PASSWORD": "p"}
    c = ProviderCredentials.from_env("PROVIDER1", env=env)
    assert (c.url, c.username, c.password) == ("https://x/login", "u", "p")


def test_credentials_missing_names_the_gaps():
    env = {"PROVIDER1_URL": "https://x/login"}  # username + password absent
    with pytest.raises(ValueError, match="PROVIDER1_USERNAME.*PROVIDER1_PASSWORD"):
        ProviderCredentials.from_env("PROVIDER1", env=env)


# --- registry ----------------------------------------------------------------

def test_example_is_registered():
    assert "example" in available()
    assert get_fetcher_class("example") is ExampleProviderFetcher


def test_unknown_provider_lists_available():
    with pytest.raises(KeyError, match="Unknown provider 'nope'.*example"):
        get_fetcher_class("nope")


def test_fetcher_from_env_builds_with_credentials():
    env = {"PROVIDER1_URL": "https://x/login", "PROVIDER1_USERNAME": "u", "PROVIDER1_PASSWORD": "p"}
    f = ExampleProviderFetcher.from_env(download_dir="downloads", env=env)
    assert isinstance(f, BaseFetcher)
    assert f.credentials.username == "u"


# --- integration: real browser against a local fake portal -------------------

_LOGIN_HTML = """<!doctype html><title>Login</title>
<form action="billing.html" method="get">
  <label for="u">Username</label><input id="u" name="u">
  <label for="p">Password</label><input id="p" name="p" type="password">
  <button type="submit">Sign in</button>
</form>"""

_BILLING_HTML = """<!doctype html><title>Billing</title>
<a href="#">Billing</a>
<a href="bill.pdf" download>Download PDF</a>"""

_PDF_BYTES = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"


@pytest.fixture
def fake_portal(tmp_path):
    """Serve a tiny login+billing site over HTTP; yield the login URL."""
    site = tmp_path / "site"
    site.mkdir()
    (site / "login.html").write_text(_LOGIN_HTML)
    (site / "billing.html").write_text(_BILLING_HTML)
    (site / "bill.pdf").write_bytes(_PDF_BYTES)

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
    server = http.server.HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        yield f"http://127.0.0.1:{port}/login.html"
    finally:
        server.shutdown()
        thread.join()


def test_fetch_latest_bill_against_fake_portal(tmp_path, fake_portal):
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright

    # Skip if the browser binary isn't installed (playwright install chromium).
    try:
        with sync_playwright() as pw:
            pw.chromium.launch(headless=True).close()
    except Exception as e:
        pytest.skip(f"chromium not available: {e}")

    download_dir = tmp_path / "downloads"
    creds = ProviderCredentials(url=fake_portal, username="u", password="p")
    fetcher = ExampleProviderFetcher(creds, download_dir=download_dir, headless=True)

    path = fetcher.fetch_latest_bill()

    assert Path(path).exists()
    assert Path(path).parent == download_dir
    assert Path(path).read_bytes().startswith(b"%PDF")
