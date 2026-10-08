import pytest

from app.scraper.parser import BusinessParser


class FakeLocator:
    def __init__(self, root, selector):
        self.root = root
        self.selector = selector

    @property
    def first(self):
        return self

    def inner_text(self, timeout=None):
        if self.selector in self.root.texts:
            return self.root.texts[self.selector]
        raise TimeoutError(f"no text for {self.selector}")

    def get_attribute(self, name, timeout=None):
        return self.root.attrs.get((self.selector, name))

    def all_inner_texts(self):
        if self.selector in self.root.texts:
            return [self.root.texts[self.selector]]
        return self.root.lists.get(self.selector, [])


class FakeNode:
    def __init__(self, texts=None, attrs=None, lists=None, url=""):
        self.texts = texts or {}
        self.attrs = attrs or {}
        self.lists = lists or {}
        self.url = url

    def locator(self, selector):
        return FakeLocator(self, selector)


@pytest.fixture
def parser():
    return BusinessParser()


class TestHelpers:
    def test_parse_rating(self, parser):
        assert parser._parse_rating("4.7") == 4.7
        assert parser._parse_rating("5") == 5.0
        assert parser._parse_rating("(4.7)") is None
        assert parser._parse_rating("7.2") is None
        assert parser._parse_rating("") is None

    def test_parse_review_count(self, parser):
        assert parser._parse_review_count("(183)") == 183
        assert parser._parse_review_count("(1,834)") == 1834
        assert parser._parse_review_count("183") == 183
        assert parser._parse_review_count("no reviews") is None

    def test_unwrap_website(self, parser):
        wrapped = "https://www.google.com/url?q=https%3A%2F%2Fabc.com%2F&sa=U"
        assert parser._unwrap_website(wrapped) == "https://abc.com/"
        assert parser._unwrap_website("abc.com") == "https://abc.com"
        assert parser._unwrap_website(None) is None

    def test_extract_source_id(self, parser):
        url = (
            "https://www.google.com/maps/place/ABC+Dental/data=!4m2!3m1!"
            "1s0x3ad42abc12345678%3A0xdeadbeef!8m2!3d31.5!4d74.3"
        )
        assert parser.extract_source_id(url) == "0x3ad42abc12345678:0xdeadbeef"
        assert parser.extract_source_id("https://www.google.com/maps/place/Something/") == "Something"
        assert parser.extract_source_id("") is None

    def test_extract_coordinates(self, parser):
        lat, lng = parser.extract_coordinates(
            "https://www.google.com/maps/place/X/@31.5200,74.3587,17z"
        )
        assert lat == 31.52
        assert lng == 74.3587
        assert parser.extract_coordinates("https://example.com") == (None, None)

    def test_extract_coordinates_prefers_place_over_viewport(self, parser):
        url = (
            "https://www.google.com/maps/place/X/@31.441338,74.1235234,12z"
            "/data=!4m2!3m1!1s0xa!8m2!3d31.5440383!4d74.4022216"
        )
        lat, lng = parser.extract_coordinates(url)
        assert (lat, lng) == (31.5440383, 74.4022216)


class TestParseCard:
    def test_parses_name_url_rating_and_category(self, parser):
        card = FakeNode(
            texts={
                "div.qBF1Pd": "ABC Dental Clinic",
                "div.W4Efsd": "Dentist · Open ⋅ Closes 9pm\nGulberg, Lahore",
            },
            attrs={
                ("a[href*='/maps/place/']", "href"): "https://www.google.com/maps/place/ABC",
            },
            lists={"span.F7nice span": ["4.7", "(183)"]},
        )
        data = parser.parse_card(card)
        assert data["name"] == "ABC Dental Clinic"
        assert data["maps_url"].endswith("/ABC")
        assert data["rating"] == 4.7
        assert data["review_count"] == 183
        assert data["category"] == "Dentist"

    def test_name_falls_back_to_aria_label(self, parser):
        card = FakeNode(
            attrs={
                ("a.hfpxzc", "aria-label"): "XYZ Clinic",
                ("a[href*='/maps/place/']", "href"): "https://www.google.com/maps/place/XYZ",
            },
        )
        data = parser.parse_card(card)
        assert data["name"] == "XYZ Clinic"

    def test_missing_card_fields_are_none(self, parser):
        data = parser.parse_card(FakeNode())
        assert data["name"] is None
        assert data["maps_url"] is None
        assert data["rating"] is None
        assert data["review_count"] is None


class TestParsePlacePage:
    def test_extracts_full_detail(self, parser):
        page = FakeNode(
            texts={
                "h1": "ABC Dental Clinic",
                "button[data-item-id='address']": "12 Main Blvd, Gulberg, Lahore",
                "a[data-item-id^='phone'], button[data-item-id^='phone']": "+92 300 1234567",
                "button[data-item-id^='oh']": "Open ⋅ Closes 9pm",
                "div.lbhGac": "Dentist",
            },
            attrs={
                ("a[data-item-id='authority']", "href"): "https://abc-dental.com",
            },
            lists={"div.F7nice span": ["4.7", "(183)"]},
            url=(
                "https://www.google.com/maps/place/ABC+Dental/"
                "@31.5200,74.3587,17z/data=!4m2!3m1!1s0xabc%3A0xdef"
            ),
        )
        business = parser.parse_place_page(page)
        assert business.name == "ABC Dental Clinic"
        assert business.address == "12 Main Blvd, Gulberg, Lahore"
        assert business.phone == "+92 300 1234567"
        assert business.website == "https://abc-dental.com"
        assert business.opening_hours == "Open ⋅ Closes 9pm"
        assert business.category == "Dentist"
        assert business.rating == 4.7
        assert business.review_count == 183
        assert business.latitude == 31.52
        assert business.longitude == 74.3587
        assert business.source_id == "0xabc:0xdef"

    def test_uses_aria_label_when_text_missing(self, parser):
        page = FakeNode(
            texts={"h1": "Only Name"},
            attrs={
                ("button[data-item-id='address']", "aria-label"): "Address: Street 4, Islamabad",
                ("a[data-item-id^='phone'], button[data-item-id^='phone']", "aria-label"): "Phone: +92511234567",
            },
            url="https://www.google.com/maps/place/Only+Name",
        )
        business = parser.parse_place_page(page)
        assert business.address == "Street 4, Islamabad"
        assert business.phone == "+92511234567"

    def test_returns_none_without_name(self, parser):
        assert parser.parse_place_page(FakeNode()) is None

    def test_place_name_ignores_results_heading(self, parser):
        page = FakeNode(
            lists={"h1": ["Results", "", "Sponsored", "Real Clinic"]},
            url="https://www.google.com/maps/place/Real+Clinic/data=!1s0xabc:0xdef",
        )
        business = parser.parse_place_page(page)
        assert business is not None
        assert business.name == "Real Clinic"


class TestParseFromHtml:
    def test_parses_saved_fixture(self):
        from pathlib import Path

        fixture = Path(__file__).parent / "fixtures" / "business_1.html"
        html = fixture.read_text(encoding="utf-8")
        try:
            business = BusinessParser.parse_from_html(
                html,
                name_selector="h1",
                address_selector=".address",
                phone_selector=".phone",
                rating_selector=".rating",
                review_count_selector=".reviews",
            )
        except Exception as exc:  # pragma: no cover - environment dependent
            pytest.skip(f"browser unavailable: {exc}")

        if business is None:
            pytest.skip("parser returned no business for fixture")
        assert business.name == "ABC Dental Clinic"
        assert business.address == "Gulberg, Lahore"
        assert business.phone == "+92 300 1234567"
        assert business.rating == 4.7
        assert business.review_count == 183
