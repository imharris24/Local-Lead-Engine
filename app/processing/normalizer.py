from typing import List, Dict, Any
import re


class Normalizer:
    """Normalizes business data for consistent comparison and storage."""

    @staticmethod
    def normalize_name(name: Optional[str]) -> str:
        """Normalize business name for comparison."""
        if not name:
            return ""
        name = name.strip()
        name = re.sub(r"[^\w\s-]", "", name)
        name = re.sub(r"\s+", " ", name)
        return name.lower()

    @staticmethod
    def normalize_phone(phone: Optional[str]) -> Optional[str]:
        """Normalize phone number to consistent format."""
        if not phone:
            return None
        digits = re.sub(r"\D", "", phone)
        if len(digits) >= 10:
            # Format: +923001234567 or 03001234567
            if digits.startswith("92") or digits.startswith("0092"):
                # International format
                return f"+{digits[:3]} {digits[3:7]}-{digits[7:]}" if len(digits) >= 10 else phone
            elif digits.startswith("0"):
                # Local Pakistani format
                if len(digits) >= 11:
                    return f"{digits[0:3]} {digits[3:7]}-{digits[7:]}"
        return phone

    @staticmethod
    def normalize_address(address: Optional[str]) -> str:
        """Normalize address for comparison."""
        if not address:
            return ""
        addr = address.strip()
        addr = re.sub(r"\s+", " ", addr)
        return addr.lower()

    @staticmethod
    def normalize_website(website: Optional[str]) -> Optional[str]:
        """Normalize website URL."""
        if not website:
            return None
        url = website.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url

    @staticmethod
    def normalize_rating(rating: Optional[float]) -> Optional[float]:
        """Normalize rating value."""
        if rating is not None:
            try:
                return round(float(rating), 1)
            except (ValueError, TypeError):
                return None
        return None


class Deduplicator:
    """Handles duplicate detection for business records."""

    def __init__(self, repository, score_weights: Dict[str, float] = None):
        self.repository = repository
        self.weights = score_weights or {
            "source_id": 1.0,
            "maps_url": 0.9,
            "phone": 0.7,
            "website": 0.6,
            "name_address": 0.4,
        }

    def is_duplicate(self, new_record: BusinessRecord, existing_record: BusinessRecord) -> bool:
        """Check if a new record is a duplicate of an existing one."""
        if not new_record.name or not existing_record.name:
            return False

        # Check source_id first (most reliable)
        if new_record.source_id and existing_record.source_id:
            if new_record.source_id == existing_record.source_id:
                return True

        # Check canonical maps URL
        if new_record.maps_url and existing_record.maps_url:
            if new_record.maps_url == existing_record.maps_url:
                return True

        # Check phone number (normalized)
        new_phone = self.repository.normalize_phone(new_record.phone) if hasattr(self.repository, 'normalize_phone') else None
        existing_phone = self.repository.normalize_phone(existing_record.phone) if hasattr(self.repository, 'normalize_phone') else None
        if new_phone and existing_phone:
            if new_phone == existing_phone:
                return True

        # Check website domain
        new_website = self.repository.normalize_website(new_record.website) if hasattr(self.repository, 'normalize_website') else None
        existing_website = self.repository.normalize_website(existing_record.website) if hasattr(self.repository, 'normalize_website') else None
        if new_website and existing_website:
            if new_website == existing_website:
                return True

        # Fallback to normalized name + address
        new_name_addr = (
            Normalizer.normalize_name(new_record.name)
            + "|"
            + Normalizer.normalize_address(new_record.address)
        )
        existing_name_addr = (
            Normalizer.normalize_name(existing_record.name)
            + "|"
            + Normalizer.normalize_address(existing_record.address)
        )
        if new_name_addr == existing_name_addr:
            return True

        return False

    def find_duplicates(self, records: List[BusinessRecord]) -> Dict[int, List[int]]:
        """Find all duplicate records in a list."""
        groups: Dict[int, List[int]] = {}
        for i, record in enumerate(records):
            groups[i] = [i]
            for j, other in enumerate(records):
                if i != j and self.is_duplicate(record, other):
                    groups[i].append(j)
        return groups

    def merge_records(self, records: List[BusinessRecord]) -> BusinessRecord:
        """Merge multiple records into one, prioritizing complete data."""
        if not records:
            raise ValueError("No records to merge")

        if len(records) == 1:
            return records[0]

        merged = BusinessRecord(
            id=records[0].id,
            source=records[0].source,
            source_id=records[0].source_id,
            name="",
            category="",
            address="",
            phone="",
            website="",
            rating=None,
            review_count=0,
            latitude=None,
            longitude=None,
            maps_url="",
            opening_hours="",
            search_keyword="",
            search_location="",
            first_seen_at=min(r.first_seen_at for r in records),
            last_seen_at=max(r.last_seen_at for r in records),
            scraped_at=max(r.scraped_at for r in records),
        )

        for record in records:
            if record.name and not merged.name:
                merged.name = record.name
            if record.category and not merged.category:
                merged.category = record.category
            if record.address and not merged.address:
                merged.address = record.address
            if record.phone and not merged.phone:
                merged.phone = record.phone
            if record.website and not merged.website:
                merged.website = record.website
            if record.rating is None and merged.rating is None and record.rating is not None:
                merged.rating = record.rating
            if merged.rating is None and record.rating is not None:
                merged.rating = record.rating
            if merged.review_count is None and record.review_count is not None:
                merged.review_count = record.review_count
            if merged.latitude is None and record.latitude is not None:
                merged.latitude = record.latitude
            if merged.longitude is None and record.longitude is not None:
                merged.longitude = record.longitude
            if record.maps_url and not merged.maps_url:
                merged.maps_url = record.maps_url
            if record.opening_hours and not merged.opening_hours:
                merged.opening_hours = record.opening_hours
            if record.search_keyword and not merged.search_keyword:
                merged.search_keyword = record.search_keyword
            if record.search_location and not merged.search_location:
                merged.search_location = record.search_location

        return merged