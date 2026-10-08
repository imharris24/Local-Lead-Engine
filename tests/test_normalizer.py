import pytest

from app.processing.normalizer import Normalizer


class TestNormalizer:
    def test_normalize_name_strips_and_lowercases(self):
        assert Normalizer.normalize_name("ABC Dental Clinic - Lahore") == "abc dental clinic - lahore"

    def test_normalize_name_handles_empty(self):
        assert Normalizer.normalize_name(None) == ""
        assert Normalizer.normalize_name("") == ""

    def test_normalize_name_collapses_whitespace(self):
        assert Normalizer.normalize_name("  Dentist   House  ") == "dentist house"

    def test_normalize_address(self):
        assert Normalizer.normalize_address("  Gulberg,   Lahore ") == "gulberg, lahore"
        assert Normalizer.normalize_address(None) == ""

    def test_normalize_phone_pakistani_local(self):
        assert Normalizer.normalize_phone("0300 1234567") == "+923001234567"
        assert Normalizer.normalize_phone("0300-1234567") == "+923001234567"

    def test_normalize_phone_international_forms_match(self):
        assert Normalizer.normalize_phone("+92 300-1234567") == "+923001234567"
        assert Normalizer.normalize_phone("0092 300 1234567") == "+923001234567"

    def test_normalize_phone_leaves_unknown_formats(self):
        assert Normalizer.normalize_phone("555-1234") == "555-1234"

    def test_normalize_phone_returns_none_for_empty(self):
        assert Normalizer.normalize_phone(None) is None
        assert Normalizer.normalize_phone("") is None

    def test_normalize_website_adds_scheme(self):
        assert Normalizer.normalize_website("example.com") == "https://example.com"

    def test_normalize_website_keeps_existing_scheme(self):
        assert Normalizer.normalize_website("http://example.com") == "http://example.com"

    def test_normalize_rating_rounds(self):
        assert Normalizer.normalize_rating(4.66) == 4.7
        assert Normalizer.normalize_rating(None) is None
        assert Normalizer.normalize_rating("not-a-number") is None
