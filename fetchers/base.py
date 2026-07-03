"""Provider fetcher framework: log into a utility portal and download a bill PDF.

One module per provider, each a `BaseFetcher` subclass that fills in two
provider-specific steps — `login` and `download_latest_bill`. The base class owns
the deterministic parts: credential loading, the Playwright browser lifecycle, and
the download directory. Playwright is imported lazily inside `fetch_latest_bill`
so this module, the credential logic, and the registry stay importable and
testable without a browser installed (mirrors the parser's lazy SDK import).

Hard rules (see CLAUDE.md):
- Fetchers are strictly READ-ONLY. They download bills; they never submit charges
  or write to any portal. Never automate Apartments.com — a human enters charges.
- Credentials come only from the environment (.env, gitignored). They are never
  logged, committed, or passed on a command line.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DOWNLOAD_DIR = Path("downloads")  # gitignored


@dataclass
class ProviderCredentials:
    url: str
    username: str
    password: str

    @classmethod
    def from_env(cls, prefix: str, env: dict | None = None) -> "ProviderCredentials":
        """Load `{PREFIX}_URL`, `{PREFIX}_USERNAME`, `{PREFIX}_PASSWORD` from the environment.

        `prefix` matches the .env convention (e.g. "PROVIDER1"). Raises a clear
        error naming the missing variables rather than leaking a partial login.
        """
        env = os.environ if env is None else env
        keys = {field: f"{prefix}_{field.upper()}" for field in ("url", "username", "password")}
        missing = [k for k in keys.values() if not env.get(k)]
        if missing:
            raise ValueError(
                f"Missing credentials for provider prefix {prefix!r}: "
                f"set {', '.join(missing)} in .env"
            )
        return cls(url=env[keys["url"]], username=env[keys["username"]], password=env[keys["password"]])


class BaseFetcher(ABC):
    """Base class for a provider fetcher. Subclasses implement `login` and
    `download_latest_bill`; the base runs the browser lifecycle around them.

    Class attributes a subclass must set:
        name        registry key, e.g. "example"
        env_prefix  credential prefix in .env, e.g. "PROVIDER1"
    """

    name: str = ""
    env_prefix: str = ""

    def __init__(
        self,
        credentials: ProviderCredentials,
        download_dir: Path | str = DEFAULT_DOWNLOAD_DIR,
        *,
        headless: bool = True,
        timeout_ms: int = 30_000,
    ):
        self.credentials = credentials
        self.download_dir = Path(download_dir)
        self.headless = headless
        self.timeout_ms = timeout_ms

    @classmethod
    def from_env(cls, download_dir: Path | str = DEFAULT_DOWNLOAD_DIR, *, headless: bool = True,
                 env: dict | None = None) -> "BaseFetcher":
        """Build a fetcher with credentials loaded from the environment."""
        if not cls.env_prefix:
            raise ValueError(f"{cls.__name__} must set env_prefix.")
        creds = ProviderCredentials.from_env(cls.env_prefix, env=env)
        return cls(creds, download_dir=download_dir, headless=headless)

    def fetch_latest_bill(self) -> Path:
        """Run the full session: launch a browser, log in, download the latest bill.

        Returns the path to the downloaded PDF. Playwright is imported here so the
        rest of the module needs neither the package nor a browser binary.
        """
        from playwright.sync_api import sync_playwright

        self.download_dir.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=self.headless)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            page.set_default_timeout(self.timeout_ms)
            try:
                self.login(page)
                return self.download_latest_bill(page, self.download_dir)
            finally:
                context.close()
                browser.close()

    @abstractmethod
    def login(self, page) -> None:
        """Navigate to the portal and authenticate with `self.credentials`."""

    @abstractmethod
    def download_latest_bill(self, page, download_dir: Path) -> Path:
        """From a logged-in session, download the most recent bill PDF. Return its path."""


# --- Registry: name -> fetcher class -------------------------------------------------

_REGISTRY: dict[str, type[BaseFetcher]] = {}


def register(cls: type[BaseFetcher]) -> type[BaseFetcher]:
    """Class decorator that registers a fetcher under its `name`."""
    if not cls.name:
        raise ValueError(f"{cls.__name__} must set a non-empty name to be registered.")
    if cls.name in _REGISTRY:
        raise ValueError(f"Duplicate fetcher name {cls.name!r} ({cls.__name__}).")
    _REGISTRY[cls.name] = cls
    return cls


def get_fetcher_class(name: str) -> type[BaseFetcher]:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(f"Unknown provider {name!r}. Available: {available() or '(none)'}") from None


def available() -> list[str]:
    return sorted(_REGISTRY)
