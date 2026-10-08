from typing import Optional
from playwright.sync_api import Browser, Page, sync_playwright


class BrowserEngine:
    """Manages Playwright browser lifecycle."""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self._browser: Optional[Browser] = None
        self._playwright = None

    def start(self) -> BrowserEngine:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        return self

    def new_page(self) -> Page:
        if self._browser is None:
            raise RuntimeError("Browser not started. Call start() first.")
        return self._browser.new_page()

    def close(self) -> None:
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    @property
    def is_connected(self) -> bool:
        return self._browser is not None and not self._browser.is_closed()