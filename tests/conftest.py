"""Shared fixtures for browser-driven tests (fetcher + full pipeline).

`fake_portal` serves a tiny login+billing site over HTTP so the real fetcher can
log in and download a PDF without any real credentials. `require_chromium` skips
a test cleanly when Playwright's browser binary isn't installed, keeping the
default suite green everywhere (`playwright install chromium` enables it).
"""
import functools
import http.server
import threading

import pytest

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


@pytest.fixture
def require_chromium():
    """Skip the test unless Playwright's chromium binary is available."""
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as pw:
            pw.chromium.launch(headless=True).close()
    except Exception as e:
        pytest.skip(f"chromium not available: {e}")
