from typing import Optional, Dict, Any
from ..database.models import BusinessRecord


class Business:
    """Domain model for a business entity."""

    def __init__(
        self,
        name: Optional[str] = None,
        category: Optional[str] = None,
        address: Optional[str] = None,
        phone: Optional[str] = None,
        website: Optional[str] = None,
        rating: Optional[float] = None,
        review_count: Optional[int] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        maps_url: Optional[str] = None,
        opening_hours: Optional[str] = None,
        source: str = "unknown",
        source_id: Optional[str] = None,
        search_keyword: str = "",
        search_location: str = "",
    ):
        self.source = source
        self.source_id = source_id
        self.name = name
        self.category = category
        self.address = address
        self.phone = phone
        self.website = website
        self.rating = rating
        self.review_count = review_count
        self.latitude = latitude
        self.longitude = longitude
        self.maps_url = maps_url
        self.opening_hours = opening_hours
        self.search_keyword = search_keyword
        self.search_location = search_location

    def to_record(self) -> BusinessRecord:
        """Convert to database BusinessRecord."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        first_seen = self._get_first_seen()
        return BusinessRecord(
            source=self.source,
            source_id=self.source_id,
            name=self.name,
            category=self.category,
            address=self.address,
            phone=self.phone,
            website=self.website,
            rating=self.rating,
            review_count=self.review_count,
            latitude=self.latitude,
            longitude=self.longitude,
            maps_url=self.maps_url,
            opening_hours=self.opening_hours,
            search_keyword="",  # set by search engine
            search_location="",  # set by search engine
            first_seen_at=first_seen,
            last_seen_at=now,
            scraped_at=now,
        )

    def _get_first_seen(self) -> str:
        """Get first_seen_at - use existing if available, otherwise now."""
        # This will be set when persisting to DB
        return ""

    def is_valid(self) -> bool:
        """Check if business has minimum required fields."""
        return self.name is not None