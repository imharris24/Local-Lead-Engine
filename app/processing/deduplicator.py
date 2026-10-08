from typing import List, Optional, Dict
from ..processing.normalizer import Normalizer


class DeduplicationEngine:
    """Engine for handling deduplication of business records."""

    def __init__(self, normalizer=None, scores: Dict[str, float] = None):
        self.normalizer = normalizer or Normalizer()
        self.scores = scores or {
            "source_id": 1.0,
            "maps_url": 0.9,
            "phone": 0.7,
            "website": 0.6,
            "name_address": 0.4,
        }

    def is_duplicate(self, new_record: object, existing_records: List[object]) -> Optional[object]:
        """Check if new_record is a duplicate of any existing record.
        Returns the existing record if duplicate, None otherwise."""
        for existing in existing_records:
            if self._is_duplicate_match(new_record, existing):
                return existing
        return None

    def _is_duplicate_match(self, new_record: object, existing_record: object) -> bool:
        """Check if two records match for deduplication."""
        # Extract fields safely
        def get_name(r):
            return getattr(r, 'name', None) or ""

        def get_source_id(r):
            return getattr(r, 'source_id', None)

        def get_maps_url(r):
            return getattr(r, 'maps_url', None)

        def get_phone(r):
            return getattr(r, 'phone', None)

        def get_website(r):
            return getattr(r, 'website', None)

        # Source/Place ID - most reliable
        new_sid = get_source_id(new_record)
        existing_sid = get_source_id(existing_record)
        if new_sid and existing_sid and new_sid == existing_sid:
            return True

        # Canonical Maps URL
        new_mu = get_maps_url(new_record)
        existing_mu = get_maps_url(existing_record)
        if new_mu and existing_mu and new_mu == existing_mu:
            return True

        # Phone number (normalized)
        new_phone = self.normalizer.normalize_phone(get_phone(new_record))
        existing_phone = self.normalizer.normalize_phone(get_phone(existing_record))
        if new_phone and existing_phone and new_phone == existing_phone:
            return True

        # Website domain
        new_wb = self.normalizer.normalize_website(get_website(new_record))
        existing_wb = self.normalizer.normalize_website(get_website(existing_record))
        if new_wb and existing_wb and new_wb == existing_wb:
            return True

        # Normalized name + address
        new_name = self.normalizer.normalize_name(get_name(new_record))
        existing_name = self.normalizer.normalize_name(get_name(existing_record))
        new_addr = self.normalizer.normalize_address(getattr(new_record, 'address', None))
        existing_addr = self.normalizer.normalize_address(getattr(existing_record, 'address', None))
        if new_name and existing_name and new_name == existing_name:
            if new_addr and existing_addr and new_addr == existing_addr:
                return True
            # Also accept if only name matches (less strict)
            if not new_addr and not existing_addr:
                return True

        return False

    def find_duplicates(self, records: List[object]) -> Dict[int, List[int]]:
        """Find all duplicate records in a list."""
        groups: Dict[int, List[int]] = {}
        for i, record in enumerate(records):
            groups[i] = [i]
            for j, other in enumerate(records):
                if i != j and self.is_duplicate(record, [other]):
                    groups[i].append(j)
        return groups

    def merge_records(self, records: List[object]) -> object:
        """Merge multiple records into one, prioritizing complete data."""
        if not records:
            raise ValueError("No records to merge")

        if len(records) == 1:
            return records[0]

        merged = type('MergedRecord', (), {})()

        # Collect all field values, prioritizing earlier records
        fields = ['name', 'category', 'address', 'phone', 'website',
                  'rating', 'review_count', 'latitude', 'longitude',
                  'maps_url', 'opening_hours']

        # First record provides base
        for field in fields:
            setattr(merged, field, getattr(records[0], field, None))

        # Fill in missing values from other records
        for record in records[1:]:
            for field in fields:
                val = getattr(record, field, None)
                current = getattr(merged, field, None)
                if val and (current is None or current == ""):
                    setattr(merged, field, val)

        # Set metadata
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        setattr(merged, 'first_seen_at', min(
            [getattr(r, 'first_seen_at', now) for r in records]))
        setattr(merged, 'last_seen_at', max(
            [getattr(r, 'last_seen_at', now) for r in records]))
        setattr(merged, 'scraped_at', max(
            [getattr(r, 'scraped_at', now) for r in records]))

        return merged