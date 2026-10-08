from datetime import datetime, timezone
from typing import Optional, Dict, Any

BUSINESS_SCHEMA = """
CREATE TABLE IF NOT EXISTS businesses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_id TEXT,
    name TEXT,
    category TEXT,
    address TEXT,
    phone TEXT,
    website TEXT,
    rating REAL,
    review_count INTEGER,
    latitude REAL,
    longitude REAL,
    maps_url TEXT,
    opening_hours TEXT,
    search_keyword TEXT,
    search_location TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    scraped_at TEXT NOT NULL,
    UNIQUE(source, source_id)
);
"""

BUSINESS_INSERT = """
INSERT INTO businesses (
    source, source_id, name, category, address, phone, website,
    rating, review_count, latitude, longitude, maps_url, opening_hours,
    search_keyword, search_location, first_seen_at, last_seen_at, scraped_at
) VALUES (
    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
);
"""

BUSINESS_SELECT_BY_ID = """
SELECT id, source, source_id, name, category, address, phone, website,
       rating, review_count, latitude, longitude, maps_url, opening_hours,
       search_keyword, search_location, first_seen_at, last_seen_at, scraped_at
FROM businesses
WHERE id = ?;
"""

BUSINESS_SELECT_BY_SOURCE_ID = """
SELECT id, source, source_id, name, category, address, phone, website,
       rating, review_count, latitude, longitude, maps_url, opening_hours,
       search_keyword, search_location, first_seen_at, last_seen_at, scraped_at
FROM businesses
WHERE source = ? AND source_id = ?;
"""

BUSINESS_SELECT_BY_NAME_ADDRESS = """
SELECT id, source, source_id, name, category, address, phone, website,
       rating, review_count, latitude, longitude, maps_url, opening_hours,
       search_keyword, search_location, first_seen_at, last_seen_at, scraped_at
FROM businesses
WHERE LOWER(name) = LOWER(?) AND LOWER(address) = LOWER(?);
"""

UPSERT_BUSINESS = """
INSERT INTO businesses (
    source, source_id, name, category, address, phone, website,
    rating, review_count, latitude, longitude, maps_url, opening_hours,
    search_keyword, search_location, first_seen_at, last_seen_at, scraped_at
) VALUES (
    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
)
ON CONFLICT(source, source_id) DO UPDATE SET
    name = EXCLUDED.name,
    category = EXCLUDED.category,
    address = EXCLUDED.address,
    phone = EXCLUDED.phone,
    website = EXCLUDED.website,
    rating = EXCLUDED.rating,
    review_count = EXCLUDED.review_count,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    maps_url = EXCLUDED.maps_url,
    opening_hours = EXCLUDED.opening_hours,
    search_keyword = EXCLUDED.search_keyword,
    search_location = EXCLUDED.search_location,
    last_seen_at = EXCLUDED.last_seen_at,
    scraped_at = EXCLUDED.scraped_at;
"""

SEARCH_HISTORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    location TEXT NOT NULL,
    result_limit INTEGER,
    discovered_count INTEGER DEFAULT 0,
    processed_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'completed',
    started_at TEXT NOT NULL,
    completed_at TEXT,
    export_path TEXT
);
"""

SEARCH_INSERT = """
INSERT INTO search_history (
    keyword, location, result_limit, discovered_count, processed_count,
    failed_count, status, started_at, completed_at, export_path
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""

SEARCH_SELECT_ALL = """
SELECT id, keyword, location, result_limit, discovered_count, processed_count,
       failed_count, status, started_at, completed_at, export_path
FROM search_history
ORDER BY started_at DESC;
"""

SEARCH_SELECT_BY_ID = """
SELECT id, keyword, location, result_limit, discovered_count, processed_count,
       failed_count, status, started_at, completed_at, export_path
FROM search_history
WHERE id = ?;
"""


class BusinessRecord:
    """Represents a business record from the database."""

    def __init__(
        self,
        id: int = 0,
        source: str = "",
        source_id: Optional[str] = None,
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
        search_keyword: str = "",
        search_location: str = "",
        first_seen_at: str = "",
        last_seen_at: str = "",
        scraped_at: str = "",
    ):
        self.id = id
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
        self.first_seen_at = first_seen_at
        self.last_seen_at = last_seen_at
        self.scraped_at = scraped_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "source_id": self.source_id,
            "name": self.name,
            "category": self.category,
            "address": self.address,
            "phone": self.phone,
            "website": self.website,
            "rating": self.rating,
            "review_count": self.review_count,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "maps_url": self.maps_url,
            "opening_hours": self.opening_hours,
            "search_keyword": self.search_keyword,
            "search_location": self.search_location,
            "first_seen_at": self.first_seen_at,
            "last_seen_at": self.last_seen_at,
            "scraped_at": self.scraped_at,
        }

    @property
    def is_complete(self) -> bool:
        return self.name is not None

    @property
    def has_website(self) -> bool:
        return self.website is not None

    @property
    def has_phone(self) -> bool:
        return self.phone is not None