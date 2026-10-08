import re
import unicodedata
from typing import Optional, List, Dict, Any
from urllib.parse import parse_qs, urlparse, unquote

from .business import Business


class BusinessParser:
    """Parses business data from Google Maps search results and place pages."""

    CARD_NAME_SELECTORS = ["div.qBF1Pd", "a.hfpxzc", "span.fontHeadlineSmall"]
    CARD_LINK_SELECTOR = "a[href*='/maps/place/']"
    CARD_RATING_SELECTOR = "span.F7nice span"
    CARD_META_SELECTOR = "div.W4Efsd"

    DETAIL_NAME_SELECTOR = "h1"
    DETAIL_ADDRESS_SELECTOR = "button[data-item-id='address']"
    DETAIL_PHONE_SELECTOR = "a[data-item-id^='phone'], button[data-item-id^='phone']"
    DETAIL_WEBSITE_SELECTOR = "a[data-item-id='authority']"
    DETAIL_HOURS_SELECTOR = "button[data-item-id^='oh']"
    DETAIL_RATING_SELECTOR = "div.F7nice span"

    # Headings that belong to the results feed, not the place panel
    NON_PLACE_HEADINGS = {"results", "sponsored", "search"}

    # ------------------------------------------------------------------
    # Search-result card
    # ------------------------------------------------------------------
    def parse_card(self, card) -> Dict[str, Any]:
        """Extract basic fields from a search-result card in the results feed."""
        data: Dict[str, Any] = {}

        data["name"] = self._card_name(card)
        data["maps_url"] = self._card_url(card)
        data["rating"], data["review_count"] = self._card_rating(card)
        data["category"] = self._card_category(card)
        return data

    def _card_name(self, card) -> Optional[str]:
        for selector in self.CARD_NAME_SELECTORS:
            locator = card.locator(selector).first
            try:
                text = BusinessParser.clean_text(locator.inner_text(timeout=1500))
                if text:
                    return text
            except Exception:
                pass
            # Some links carry the name only in aria-label
            try:
                label = BusinessParser.clean_text(
                    locator.get_attribute("aria-label", timeout=1000)
                )
                if label:
                    return label
            except Exception:
                pass
        return None

    def _card_url(self, card) -> Optional[str]:
        try:
            href = card.locator(self.CARD_LINK_SELECTOR).first.get_attribute(
                "href", timeout=1500
            )
            return href if href else None
        except Exception:
            return None

    def _card_rating(self, card) -> (Optional[float], Optional[int]):
        rating = None
        reviews = None

        for selector in (self.CARD_RATING_SELECTOR, "div.F7nice span", self.CARD_META_SELECTOR):
            try:
                texts = card.locator(selector).all_inner_texts()
            except Exception:
                continue
            for text in texts:
                cleaned = self.clean_text(text)
                if not cleaned:
                    continue
                if rating is None:
                    parsed = self._parse_rating(cleaned)
                    if parsed is not None:
                        rating = parsed
                        continue
                if reviews is None:
                    parsed = self._parse_review_count(cleaned)
                    if parsed is not None:
                        reviews = parsed

        # Layouts that expose "4.9 stars" only via aria-label
        if rating is None:
            try:
                label = card.locator("[aria-label*='star']").first.get_attribute(
                    "aria-label", timeout=800
                )
            except Exception:
                label = None
            if label:
                match = re.search(r"(\d+(?:\.\d+)?)\s*star", label, re.I)
                if match:
                    rating = float(match.group(1))

        # Layouts that render "(183)" anywhere on the card
        if reviews is None:
            try:
                raw = card.inner_text(timeout=1000)
            except Exception:
                raw = None
            if raw:
                match = re.search(r"\(([\d,]+)\)", raw)
                if match:
                    reviews = int(match.group(1).replace(",", ""))
        return rating, reviews

    def _card_category(self, card) -> Optional[str]:
        """First metadata line of a card is normally the category."""
        try:
            texts = card.locator(self.CARD_META_SELECTOR).all_inner_texts()
        except Exception:
            return None
        for text in texts:
            line = (text or "").strip()
            if not line:
                continue
            # Lines look like "Dentist · Open ⋅ Closes 9pm"
            category = line.split("·")[0].strip()
            if category and not category[0].isdigit():
                return category
        return None

    # ------------------------------------------------------------------
    # Place (detail) page
    # ------------------------------------------------------------------
    def parse_place_page(self, page) -> Optional[Business]:
        """Extract full details from an open place/detail panel."""
        name = self._place_name(page)
        if not name:
            return None

        business = Business(name=name)
        business.maps_url = page.url
        business.source_id = self.extract_source_id(page.url)
        business.latitude, business.longitude = self.extract_coordinates(page.url)

        business.address = self._labelled_text(
            page, self.DETAIL_ADDRESS_SELECTOR, ("Address",)
        )
        business.phone = self._labelled_text(
            page, self.DETAIL_PHONE_SELECTOR, ("Phone", "Call")
        )
        business.website = self._website_href(page)
        business.opening_hours = self._first_text(page, [self.DETAIL_HOURS_SELECTOR])

        rating, reviews = self._detail_rating(page)
        business.rating = rating
        business.review_count = reviews

        business.category = self._first_text(
            page, ["div.lbhGac", "span.HlvWz", "button.DkEaL"]
        )
        return business

    def _place_name(self, page) -> Optional[str]:
        """The results feed also renders an ``h1`` ("Results"); skip those."""
        try:
            headings = page.locator(self.DETAIL_NAME_SELECTOR).all_inner_texts()
        except Exception:
            return None
        name = None
        for text in headings:
            cleaned = self.clean_text(text)
            if cleaned and cleaned.lower() not in self.NON_PLACE_HEADINGS:
                name = cleaned
        return name

    def _detail_rating(self, page) -> (Optional[float], Optional[int]):
        try:
            texts = page.locator(self.DETAIL_RATING_SELECTOR).all_inner_texts()
        except Exception:
            return None, None
        rating = None
        reviews = None
        for text in texts:
            cleaned = (text or "").strip()
            if rating is None:
                parsed = self._parse_rating(cleaned)
                if parsed is not None:
                    rating = parsed
                    continue
            if reviews is None:
                parsed = self._parse_review_count(cleaned)
                if parsed is not None:
                    reviews = parsed
        if rating is None or reviews is None:
            # aria-label fallback, e.g. "4.7 stars, 183 reviews"
            try:
                label = page.locator(
                    "button[aria-label*='star'], button[aria-label*='review']"
                ).first.get_attribute("aria-label", timeout=1000)
            except Exception:
                label = None
            if label:
                if rating is None:
                    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:star|stars)", label, re.I)
                    if match:
                        rating = float(match.group(1))
                if reviews is None:
                    match = re.search(r"([\d,]+)\s*review", label, re.I)
                    if match:
                        reviews = int(match.group(1).replace(",", ""))
        return rating, reviews

    def _website_href(self, page) -> Optional[str]:
        try:
            href = page.locator(self.DETAIL_WEBSITE_SELECTOR).first.get_attribute(
                "href", timeout=1500
            )
        except Exception:
            href = None
        return self._unwrap_website(href)

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _first_text(root, selectors: List[str], timeout: int = 1500) -> Optional[str]:
        for selector in selectors:
            try:
                text = root.locator(selector).first.inner_text(timeout=timeout)
            except Exception:
                continue
            text = BusinessParser.clean_text(text)
            if text:
                return text
        return None

    @staticmethod
    def _labelled_text(root, selector: str, prefixes: tuple) -> Optional[str]:
        """Read a button/link whose visible text or aria-label is prefixed."""
        try:
            locator = root.locator(selector).first
        except Exception:
            return None

        for getter in ("inner_text", "aria-label"):
            try:
                if getter == "inner_text":
                    value = locator.inner_text(timeout=1500)
                else:
                    value = locator.get_attribute("aria-label", timeout=1000)
            except Exception:
                continue
            value = BusinessParser.clean_text(value)
            if not value:
                continue
            for prefix in prefixes:
                if value.lower().startswith(prefix.lower() + ":"):
                    value = value[len(prefix) + 1 :].strip()
            if value:
                return value
        return None

    @staticmethod
    def _parse_rating(text: str) -> Optional[float]:
        if not text:
            return None
        match = re.fullmatch(r"(\d+(?:\.\d+)?)", text.strip())
        if not match:
            return None
        try:
            value = float(match.group(1))
        except ValueError:
            return None
        return value if 0 <= value <= 5 else None

    @staticmethod
    def _parse_review_count(text: str) -> Optional[int]:
        if not text:
            return None
        cleaned = text.strip().strip("()").replace(",", "")
        if not cleaned.isdigit():
            return None
        return int(cleaned)

    @staticmethod
    def _unwrap_website(href: Optional[str]) -> Optional[str]:
        """Follow google.com/url?q= redirects and normalise the URL."""
        if not href:
            return None
        href = href.strip()
        try:
            parsed = urlparse(href)
            if parsed.netloc.endswith("google.com") and parsed.path == "/url":
                target = parse_qs(parsed.query).get("q") or parse_qs(
                    parsed.query
                ).get("url")
                if target:
                    href = unquote(target[0])
        except Exception:
            pass
        if not href.startswith(("http://", "https://")):
            href = "https://" + href.lstrip("/")
        return href

    @staticmethod
    def extract_source_id(url: str) -> Optional[str]:
        """Pull a stable place identifier out of a Google Maps URL."""
        if not url:
            return None

        # Prefer the place-id form (0x...:0x...) over echoed query fragments
        # such as "!1sdentists+Lahore".
        matches = re.findall(r"!1s([^!]+)", url)
        for match in matches:
            candidate = unquote(match)
            if re.fullmatch(r"0x[0-9a-fA-F]+:0x[0-9a-fA-F]+", candidate):
                return candidate

        match = re.search(r"/maps/place/([^/?]+)", url)
        if match:
            return unquote(match.group(1))

        if matches:
            return unquote(matches[-1])
        return None

    @staticmethod
    def clean_text(value: Optional[str]) -> Optional[str]:
        """Strip icons/private-use glyphs and collapse whitespace."""
        if not value:
            return value
        cleaned = "".join(
            ch
            for ch in value
            if unicodedata.category(ch) not in ("Co", "Cn", "Cc") or ch.isspace()
        )
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned or None

    @staticmethod
    def extract_coordinates(url: str) -> (Optional[float], Optional[float]):
        # Prefer the place coordinates (!3d...!4d...) over the map viewport
        # centre in "@lat,lng", which lags behind the opened place.
        match = re.search(r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)", url or "")
        if match:
            return float(match.group(1)), float(match.group(2))
        match = re.search(r"@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", url or "")
        if not match:
            return None, None
        return float(match.group(1)), float(match.group(2))

    # ------------------------------------------------------------------
    # Legacy helpers
    # ------------------------------------------------------------------
    @staticmethod
    def parse_basic_info(
        page,
        name_selector: str = "",
        address_selector: str = "",
        phone_selector: str = "",
        website_selector: str = "",
        rating_selector: str = "",
        review_count_selector: str = "",
    ) -> Dict[str, Any]:
        """Parse basic business information from a page."""
        result: Dict[str, Any] = {}

        for field, selector in (
            ("name", name_selector),
            ("address", address_selector),
            ("phone", phone_selector),
            ("website", website_selector),
        ):
            result[field] = BusinessParser._first_text(page, [selector]) if selector else None

        result["rating"] = None
        if rating_selector:
            text = BusinessParser._first_text(page, [rating_selector])
            result["rating"] = BusinessParser._parse_rating(text) if text else None

        result["review_count"] = None
        if review_count_selector:
            text = BusinessParser._first_text(page, [review_count_selector])
            if text:
                digits = re.sub(r"\D", "", text)
                result["review_count"] = int(digits) if digits else None

        return result

    @staticmethod
    def extract_maps_url(page) -> Optional[str]:
        """Extract maps URL from page."""
        try:
            links = page.locator("a").all()
            for link in links:
                href = link.get_attribute("href")
                if href and ("maps.google.com" in href or "google.com/maps" in href):
                    return href
            return None
        except Exception:
            return None

    @staticmethod
    def parse_from_html(html: str, **selectors) -> Optional[Business]:
        """Parse business from raw HTML content."""
        from playwright.sync_api import sync_playwright

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                try:
                    page = browser.new_page()
                    page.set_content(html)
                    business = Business()
                    parsed = BusinessParser.parse_basic_info(page, **selectors)

                    if parsed.get("name"):
                        business.name = parsed["name"]
                    if parsed.get("address"):
                        business.address = parsed["address"]
                    if parsed.get("phone"):
                        business.phone = parsed["phone"]
                    if parsed.get("website"):
                        business.website = parsed["website"]
                    if parsed.get("rating") is not None:
                        business.rating = parsed["rating"]
                    if parsed.get("review_count") is not None:
                        business.review_count = parsed["review_count"]

                    business.maps_url = BusinessParser.extract_maps_url(page)
                    return business if business.is_valid() else None
                finally:
                    browser.close()
        except Exception:
            return None
