"""Tests for the provider fetcher framework.

The credential + registry tests are pure (no Playwright, no browser, no network).
The integration test drives the real `example` fetcher against a locally served
fake portal (see the `fake_portal` / `require_chromium` fixtures in conftest.py);
it skips automatically when the browser binary isn't installed.
"""
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

def test_fetch_latest_bill_against_fake_portal(tmp_path, fake_portal, require_chromium):
    download_dir = tmp_path / "downloads"
    creds = ProviderCredentials(url=fake_portal, username="u", password="p")
    fetcher = ExampleProviderFetcher(creds, download_dir=download_dir, headless=True)

    path = fetcher.fetch_latest_bill()

    assert Path(path).exists()
    assert Path(path).parent == download_dir
    assert Path(path).read_bytes().startswith(b"%PDF")
