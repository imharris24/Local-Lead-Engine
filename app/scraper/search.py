from typing import List, Dict, Any
from datetime import datetime, timezone


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
        self.limit = limit


class SearchResult:
    """Represents a single business result from a search."""

    def __init__(
        self,
        name: str,
        source: str,
        source_id: Optional[str],
        maps_url: Optional[str],
        rating: Optional[float],
        review_count: Optional[int],
        latitude: Optional[float],
        longitude: Optional[float],
    ):
        self.name = name
        self.source = source
        self.source_id = source_id
        self.maps_url = maps_url
        self.rating = rating
        self.review_count = review_count
        self.latitude = latitude
        self.longitude = longitude


class SearchEngine:
    """Handles search workflow orchestration."""

    def __init__(self, config: SearchConfig, repository):
        self.config = config
        self.repository = repository
        self.discovered = 0
        self.processed = 0
        self.errors = 0

    def record_search(self) -> int:
        """Record a new search in the database and return its ID."""
        search_repo = self.repository if hasattr(self.repository, 'insert_search') else None
        if search_repo:
            return search_repo.insert_search(
                keyword=self.config.keyword,
                location=self.config.location,
                result_limit=self.config.limit,
            )
        return 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "keyword": self.config.keyword,
            "location": self.config.location,
            "limit": self.config.limit,
            "discovered": self.discovered,
            "processed": self.processed,
            "errors": self.errors,
        }