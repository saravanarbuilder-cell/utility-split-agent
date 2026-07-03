"""Template fetcher for a generic utility portal.

Copy this file to `fetchers/<your_provider>.py`, change `name`/`env_prefix`, and
adjust the selectors to match your provider's login and billing pages. The logic
here is real and runnable — a standard username/password login followed by
clicking a "download PDF" link — but the selectors are placeholders. Every portal
is laid out differently, so pointing this at a real site means updating the
`get_by_*` / CSS selectors below to match it.

Register the class with `@register` and it becomes available to the CLI as
`--fetch <name>`.
"""

from __future__ import annotations

from pathlib import Path

from fetchers.base import BaseFetcher, register


@register
class ExampleProviderFetcher(BaseFetcher):
    name = "example"
    env_prefix = "PROVIDER1"  # reads PROVIDER1_URL / _USERNAME / _PASSWORD from .env

    def login(self, page) -> None:
        page.goto(self.credentials.url)
        # --- adjust these selectors to the real login form ---
        page.get_by_label("Username").fill(self.credentials.username)
        page.get_by_label("Password").fill(self.credentials.password)
        page.get_by_role("button", name="Sign in").click()
        # Wait for something that only appears once logged in.
        page.wait_for_load_state("networkidle")

    def download_latest_bill(self, page, download_dir: Path) -> Path:
        # --- adjust to navigate to the billing page and trigger the PDF download ---
        page.get_by_role("link", name="Billing").click()
        with page.expect_download() as download_info:
            page.get_by_role("link", name="Download PDF").first.click()
        download = download_info.value

        target = download_dir / (download.suggested_filename or f"{self.name}_bill.pdf")
        download.save_as(target)
        return target
