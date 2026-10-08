from types import SimpleNamespace

from app.processing.deduplicator import DeduplicationEngine


def make(**kwargs):
    defaults = dict(
        source="google_maps",
        source_id=None,
        name="ABC Dental",
        address="Gulberg, Lahore",
        phone=None,
        website=None,
        maps_url=None,
        rating=4.5,
        review_count=10,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestDeduplicationEngine:
    def setup_method(self):
        self.engine = DeduplicationEngine()

    def test_duplicate_by_source_id(self):
        a = make(source_id="0xabc:0xdef")
        b = make(source_id="0xabc:0xdef", name="Completely Different")
        assert self.engine.is_duplicate(b, [a]) is a

    def test_duplicate_by_maps_url(self):
        a = make(maps_url="https://www.google.com/maps/place/ABC")
        b = make(maps_url="https://www.google.com/maps/place/ABC")
        assert self.engine.is_duplicate(b, [a]) is a

    def test_duplicate_by_phone(self):
        a = make(phone="0300 1234567")
        b = make(phone="0300-1234567", name="Other Shop")
        assert self.engine.is_duplicate(b, [a]) is a

    def test_duplicate_by_website(self):
        a = make(website="https://abc-dental.com")
        b = make(website="abc-dental.com", name="Other Shop")
        assert self.engine.is_duplicate(b, [a]) is a

    def test_duplicate_by_name_and_address(self):
        a = make()
        b = make(name="ABC   Dental!", address="gulberg, lahore")
        assert self.engine.is_duplicate(b, [a]) is a

    def test_not_duplicate(self):
        a = make()
        b = make(name="XYZ Clinic", address="DHA, Lahore", phone="042111222333")
        assert self.engine.is_duplicate(b, [a]) is None

    def test_find_duplicates_groups_records(self):
        a = make(source_id="same")
        b = make(source_id="same")
        c = make(source_id="other", name="Third", address="Other Road")
        groups = self.engine.find_duplicates([a, b, c])
        assert 1 in groups[0]
        assert groups[2] == [2]

    def test_merge_records_prefers_existing_values(self):
        a = make(phone="0300 1234567", website=None, source_id="x")
        b = make(phone=None, website="https://abc.com", source_id="x")
        merged = self.engine.merge_records([a, b])
        assert merged.phone == "0300 1234567"
        assert merged.website == "https://abc.com"

    def test_merge_single_record_returns_itself(self):
        a = make()
        assert self.engine.merge_records([a]) is a
