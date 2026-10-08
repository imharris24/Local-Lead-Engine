from typing import Optional, List, Dict, Any
from ..scraper.business import Business


class BusinessParser:
    """Parses business data from search result pages."""

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

        try:
            if name_selector:
                name = page.locator(name_selector).first.inner_text()
                result["name"] = name.strip() if name else None
        except Exception:
            result["name"] = None

        try:
            if address_selector:
                address = page.locator(address_selector).first.inner_text()
                result["address"] = address.strip() if address else None
        except Exception:
            result["address"] = None

        try:
            if phone_selector:
                phone = page.locator(phone_selector).first.inner_text()
                result["phone"] = phone.strip() if phone else None
        except Exception:
            result["phone"] = None

        try:
            if website_selector:
                website = page.locator(website_selector).first.inner_text()
                result["website"] = website.strip() if website else None
        except Exception:
            result["website"] = None

        try:
            if rating_selector:
                rating = page.locator(rating_selector).first.inner_text()
                result["rating"] = (
                    float(rating.strip()) if rating else None
                )
        except Exception:
            result["rating"] = None

        try:
            if review_count_selector:
                reviews = page.locator(review_count_selector).first.inner_text()
                result["review_count"] = (
                    int(reviews.strip()) if reviews else None
                )
        except Exception:
            result["review_count"] = None

        return result

    @staticmethod
    def extract_maps_url(page) -> Optional[str]:
        """Extract maps URL from page."""
        try:
            # Look for common maps URL patterns
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
                page = p.chromium.launch(headless=True).new_page()
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

        except Exception:
            return None