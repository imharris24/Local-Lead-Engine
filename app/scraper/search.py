import re
import time
from typing import Optional, Dict, Any, List
from urllib.parse import quote_plus

from .business import Business
from .parser import BusinessParser
from ..config import settings
from ..logging import logger
from ..processing.normalizer import Normalizer


class SearchConfig:
    """Configuration for a single search job."""

    def __init__(
        self,
        keyword: str,
        location: str,
        limit: int = 100,
    ):
        self.keyword = keyword
        self.location = location
        self.limit = int(limit)

    @property
    def query(self) -> str:
        return f"{self.keyword} {self.location}".strip()

    @property
    def slug(self) -> str:
        return slugify(f"{self.keyword}_{self.location}")

    def build_url(self) -> str:
        base = "https://www.google.com/maps/search/"
        query = f"{quote_plus(self.keyword)}+{quote_plus(self.location)}"
        return f"{base}{query}?gl=country-pk&hl=en"


def slugify(value: str) -> str:
    """Turn an arbitrary string into a filesystem-friendly slug."""
    value = value.strip().lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_-]+", "_", value)
    return value.strip("_") or "leads"


class SearchEngine:
    """Orchestrates discovery, extraction and persistence for one search job."""

    FEED_SELECTOR = "div[role='feed']"
    CARD_SELECTOR = "div[role='feed'] div[role='article']"
    PLACE_URL_MARKER = "/maps/place/"
    END_OF_RESULTS_SCROLLS = 6
    MAX_CARD_SCROLLS = 40

    def __init__(self, config: SearchConfig, repository, parser: Optional[BusinessParser] = None):
        self.config = config
        self.repository = repository
        self.parser = parser or BusinessParser()
        self.discovered = 0
        self.processed = 0
        self.new = 0
        self.duplicates = 0
        self.errors = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self, page) -> None:
        """Navigate to the search and collect up to ``config.limit`` businesses."""
        url = self.config.build_url()
        logger.info(f"Navigating to search: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        self._handle_consent(page)

        if self.PLACE_URL_MARKER in page.url:
            # Query resolved straight to a single place
            business = self.parser.parse_place_page(page)
            if business:
                self.discovered = 1
                self._store(business)
            else:
                self.errors += 1
            return

        self._wait_for_results(page)
        self._collect(page)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "keyword": self.config.keyword,
            "location": self.config.location,
            "limit": self.config.limit,
            "discovered": self.discovered,
            "processed": self.processed,
            "new": self.new,
            "duplicates": self.duplicates,
            "errors": self.errors,
        }

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------
    def _handle_consent(self, page) -> None:
        """Dismiss Google's consent interstitial when present."""
        try:
            if page.locator("form[action*='consent']").count() == 0:
                return
            for label in ("Reject all", "Accept all", "I agree"):
                button = page.get_by_role("button", name=label)
                if button.count():
                    button.first.click(timeout=5000)
                    logger.info(f"Dismissed consent dialog via '{label}'")
                    return
        except Exception as exc:
            logger.debug(f"Consent handling skipped: {exc}")

    def _wait_for_results(self, page) -> None:
        logger.info("Waiting for search results...")
        try:
            page.wait_for_selector(self.FEED_SELECTOR, timeout=30000)
        except Exception:
            # Some layouts surface articles before the feed landmark exists
            page.wait_for_selector("div[role='article']", timeout=15000)
        page.wait_for_timeout(2500)
        logger.info("Search results loaded")

    # ------------------------------------------------------------------
    # Collection loop
    # ------------------------------------------------------------------
    def _collect(self, page) -> None:
        limit = self.config.limit
        index = 0
        stagnant = 0
        seen: set = set()

        delay = float(settings.retry_delay or 1)
        page.wait_for_timeout(1000)

        while self.processed < limit and stagnant < 5:
            logger.info(
                f"Processing business {index + 1} "
                f"(collected {self.processed}/{limit})"
            )
            if not self._ensure_card_visible(page, index):
                logger.info("Reached the end of the available results")
                break

            card = page.locator(self.CARD_SELECTOR).nth(index)
            try:
                self.discovered = max(self.discovered, page.locator(self.CARD_SELECTOR).count())
            except Exception:
                pass

            business = self._process_card(page, card, index + 1)
            index += 1

            if business is None:
                self.errors += 1
                stagnant += 1
                continue

            key = business.source_id or (
                f"{(business.name or '').lower()}|{(business.address or '').lower()}"
            )
            if key in seen:
                stagnant += 1
                logger.info(f"Skipping duplicate: {business.name} (stagnant {stagnant}/5)")
                page.wait_for_timeout(delay)
                continue

            seen.add(key)
            stored = self._store(business)
            stagnant = 0 if stored else stagnant + 1
            page.wait_for_timeout(delay)

        try:
            self.discovered = max(self.discovered, page.locator(self.CARD_SELECTOR).count())
        except Exception:
            pass

    def _ensure_card_visible(self, page, index: int) -> bool:
        """Make sure card ``index`` exists and is scrolled into view."""
        cards = page.locator(self.CARD_SELECTOR)
        if cards.count() > index:
            try:
                cards.nth(index).scroll_into_view_if_needed(timeout=3000)
                return True
            except Exception:
                pass

        try:
            feed = page.locator(self.FEED_SELECTOR).first
            feed.wait_for(state="attached", timeout=10000)
        except Exception:
            return False

        no_growth = 0
        for _ in range(self.MAX_CARD_SCROLLS):
            before = cards.count()
            if before > index:
                try:
                    cards.nth(index).scroll_into_view_if_needed(timeout=3000)
                    return True
                except Exception:
                    pass
            try:
                feed.evaluate(
                    "el => el.scrollTo({ top: el.scrollHeight, behavior: 'instant' })"
                )
            except Exception:
                return cards.count() > index
            page.wait_for_timeout(1200)
            after = cards.count()
            self.discovered = max(self.discovered, after)
            if after > index:
                try:
                    cards.nth(index).scroll_into_view_if_needed(timeout=3000)
                except Exception:
                    pass
                return True
            no_growth = no_growth + 1 if after == before else 0
            if no_growth >= self.END_OF_RESULTS_SCROLLS:
                return False
        return cards.count() > index

    # ------------------------------------------------------------------
    # Per-business extraction
    # ------------------------------------------------------------------
    def _process_card(self, page, card, position: int) -> Optional[Business]:
        attempts = max(1, int(settings.retry_attempts or 1))
        base_delay = float(settings.retry_delay or 1)
        backoff = float(settings.retry_backoff or 2)

        last_error: Optional[Exception] = None
        for attempt in range(1, attempts + 1):
            try:
                return self._extract_one(page, card, position)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    f"Business {position} attempt {attempt}/{attempts} failed: {exc}"
                )
                if attempt < attempts:
                    time.sleep(base_delay * (backoff ** (attempt - 1)))

        logger.error(f"Business {position} failed after {attempts} attempts: {last_error}")
        return None

    def _extract_one(self, page, card, position: int) -> Optional[Business]:
        basic = self.parser.parse_card(card)
        name = basic.get("name")
        if not name:
            raise ValueError("card did not expose a business name")

        business = Business(
            name=name,
            category=basic.get("category"),
            rating=basic.get("rating"),
            review_count=basic.get("review_count"),
            maps_url=basic.get("maps_url"),
            source="google_maps",
            source_id=self.parser.extract_source_id(basic.get("maps_url") or ""),
            search_keyword=self.config.keyword,
            search_location=self.config.location,
        )
        business.latitude, business.longitude = self.parser.extract_coordinates(
            business.maps_url or ""
        )

        detail = self._open_and_parse(page, card)
        if detail:
            business.category = detail.category or business.category
            business.address = detail.address or business.address
            business.phone = detail.phone or business.phone
            business.website = detail.website or business.website
            business.opening_hours = detail.opening_hours or business.opening_hours
            business.rating = detail.rating if detail.rating is not None else business.rating
            business.review_count = (
                detail.review_count if detail.review_count is not None else business.review_count
            )
            business.latitude = detail.latitude or business.latitude
            business.longitude = detail.longitude or business.longitude
            business.maps_url = detail.maps_url or business.maps_url
            business.source_id = detail.source_id or business.source_id

        if not business.source_id:
            business.source_id = (
                f"{Normalizer.normalize_name(business.name)}|"
                f"{Normalizer.normalize_address(business.address)}"
            )
        return business

    def _open_and_parse(self, page, card) -> Optional[Business]:
        """Open a result's detail panel, parse it, then return to the feed."""
        logger.debug(f"Opening card; current url: {page.url}")
        if self.PLACE_URL_MARKER in page.url:
            # Previous close did not fully restore the search URL
            logger.debug("Still on a place page; returning to the results feed first")
            try:
                page.go_back(wait_until="domcontentloaded", timeout=10000)
                page.wait_for_selector(self.FEED_SELECTOR, timeout=8000)
            except Exception:
                pass
        try:
            card.click(timeout=8000)
        except Exception:
            link = card.locator("a[href*='/maps/place/']").first
            link.click(timeout=8000)

        try:
            page.wait_for_url(re.compile(self.PLACE_URL_MARKER), timeout=15000)
            logger.debug(f"Navigated to place: {page.url}")
            # The feed also renders an <h1>, so keep re-parsing until the
            # panel exposes real fields (address/phone/website/hours).
            detail = None
            deadline = time.time() + 15
            while time.time() < deadline:
                detail = self.parser.parse_place_page(page)
                if detail and any(
                    (
                        detail.address,
                        detail.phone,
                        detail.website,
                        detail.opening_hours,
                    )
                ):
                    break
                page.wait_for_timeout(600)
            return detail
        finally:
            self._close_detail(page, card)

    def _close_detail(self, page, card) -> None:
        """Return from a place panel back to the results feed."""
        try:
            if (
                self.PLACE_URL_MARKER not in page.url
                and page.locator(self.FEED_SELECTOR).count() > 0
            ):
                return
        except Exception:
            pass

        for action in ("escape", "back"):
            try:
                if action == "escape":
                    page.keyboard.press("Escape")
                else:
                    page.go_back(wait_until="domcontentloaded", timeout=10000)
                page.wait_for_selector(self.FEED_SELECTOR, timeout=8000)
                if self.PLACE_URL_MARKER in page.url:
                    logger.debug(f"Feed visible but url still {page.url}")
                    continue
                logger.debug(f"Returned to results feed via {action}")
                return
            except Exception:
                continue

        try:
            page.go_back(wait_until="domcontentloaded", timeout=10000)
            page.wait_for_selector(self.FEED_SELECTOR, timeout=8000)
        except Exception as exc:
            logger.warning(f"Could not return to the results feed: {exc}")

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _store(self, business: Business) -> bool:
        """Upsert a business into SQLite. Returns True when the row is new."""
        if not business:
            return False

        business.search_keyword = self.config.keyword
        business.search_location = self.config.location
        if business.source != "google_maps":
            business.source = "google_maps"

        business.phone = Normalizer.normalize_phone(business.phone)
        business.website = Normalizer.normalize_website(business.website)
        business.rating = Normalizer.normalize_rating(business.rating)

        record = business.to_record()

        existing = None
        if business.source_id:
            existing = self.repository.get_by_source_id(business.source, business.source_id)
        if existing is None:
            matches = self.repository.search_by_name_address(
                business.name or "", business.address or ""
            )
            existing = matches[0] if matches else None

        try:
            self.repository.upsert(record)
        except Exception as exc:
            logger.error(f"Failed to persist '{business.name}': {exc}")
            self.errors += 1
            return False

        self.processed += 1
        if existing is None:
            self.new += 1
            logger.info(f"New business {self.processed}: {business.name}")
        else:
            self.duplicates += 1
            logger.info(
                f"Updated business {self.processed}: {business.name} (duplicate)"
            )
        return True
