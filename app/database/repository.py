from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from .models import BusinessRecord, BUSINESS_SCHEMA, BUSINESS_INSERT, UPSERT_BUSINESS, SEARCH_INSERT, SEARCH_SELECT_ALL, SEARCH_HISTORY_SCHEMA, BUSINESS_SELECT_BY_ID, BUSINESS_SELECT_BY_SOURCE_ID, BUSINESS_SELECT_BY_NAME_ADDRESS
from ..database.connection import DatabaseConnection


class BusinessRepository:
    """Repository for business record operations."""

    def __init__(self, db: DatabaseConnection):
        self.db = db

    def initialize(self) -> None:
        """Create tables if they don't exist."""
        conn = self.db.connect()
        conn.executescript(BUSINESS_SCHEMA)
        conn.executescript(SEARCH_HISTORY_SCHEMA)
        conn.close()

    def upsert(self, record: object) -> object:
        """Insert or update a business record."""
        conn = self.db.connect()
        now = datetime.now(timezone.utc).isoformat()

        # Use getattr with defaults for safe attribute access
        source = getattr(record, 'source', 'unknown')
        source_id = getattr(record, 'source_id', None)
        name = getattr(record, 'name', None)
        category = getattr(record, 'category', None)
        address = getattr(record, 'address', None)
        phone = getattr(record, 'phone', None)
        website = getattr(record, 'website', None)
        rating = getattr(record, 'rating', None)
        review_count = getattr(record, 'review_count', None)
        latitude = getattr(record, 'latitude', None)
        longitude = getattr(record, 'longitude', None)
        maps_url = getattr(record, 'maps_url', None)
        opening_hours = getattr(record, 'opening_hours', None)
        search_keyword = getattr(record, 'search_keyword', '')
        search_location = getattr(record, 'search_location', '')
        first_seen_at = getattr(record, 'first_seen_at', now)
        last_seen_at = now
        scraped_at = now

        conn.execute(UPSERT_BUSINESS, (
            source, source_id, name, category, address, phone, website,
            rating, review_count, latitude, longitude, maps_url, opening_hours,
            search_keyword, search_location, first_seen_at, last_seen_at, scraped_at
        ))
        conn.commit()
        conn.close()
        return record

    def get_by_id(self, business_id: int) -> Optional[BusinessRecord]:
        """Get a business record by ID."""
        conn = self.db.connect()
        cursor = conn.execute(BUSINESS_SELECT_BY_ID, (business_id,))
        row = cursor.fetchone()
        conn.close()
        if row is None:
            return None
        return BusinessRecord(*row)

    def get_by_source_id(self, source: str, source_id: str) -> Optional[BusinessRecord]:
        """Get a business record by source and source_id."""
        conn = self.db.connect()
        cursor = conn.execute(BUSINESS_SELECT_BY_SOURCE_ID, (source, source_id))
        row = cursor.fetchone()
        conn.close()
        if row is None:
            return None
        return BusinessRecord(*row)

    def search_by_name_address(self, name: str, address: str) -> List[BusinessRecord]:
        """Search businesses by normalized name and address."""
        conn = self.db.connect()
        cursor = conn.execute(BUSINESS_SELECT_BY_NAME_ADDRESS, (name, address))
        rows = cursor.fetchall()
        conn.close()
        return [BusinessRecord(*row) for row in rows]

    def get_all(self) -> List[BusinessRecord]:
        """Get all business records."""
        conn = self.db.connect()
        cursor = conn.execute("SELECT * FROM businesses")
        rows = cursor.fetchall()
        conn.close()
        return [BusinessRecord(*row) for row in rows]

    def count(self) -> int:
        """Get total business count."""
        conn = self.db.connect()
        cursor = conn.execute("SELECT COUNT(*) FROM businesses")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def delete_duplicates(self) -> int:
        """Remove duplicate business records, keeping the most recent."""
        conn = self.db.connect()
        cursor = conn.execute("""
            DELETE FROM businesses
            WHERE id NOT IN (
                SELECT MAX(id)
                FROM businesses
                GROUP BY LOWER(name), LOWER(address)
            )
        """)
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted

    def insert_search(
        self,
        keyword: str,
        location: str,
        result_limit: int,
        discovered_count: int = 0,
        processed_count: int = 0,
        failed_count: int = 0,
        status: str = "pending",
    ) -> int:
        """Insert a search record and return its ID."""
        now = datetime.now(timezone.utc).isoformat()
        conn = self.db.connect()
        cursor = conn.execute(
            SEARCH_INSERT,
            (keyword, location, result_limit, discovered_count, processed_count,
             failed_count, status, now, None, None)
        )
        search_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return search_id

    def update_search(
        self,
        search_id: int,
        discovered_count: int = None,
        processed_count: int = None,
        failed_count: int = None,
        status: str = None,
        export_path: str = None,
        completed_at: str = None,
    ) -> None:
        """Update a search record."""
        conn = self.db.connect()
        updates = []
        params = []

        if discovered_count is not None:
            updates.append("discovered_count = ?")
            params.append(discovered_count)
        if processed_count is not None:
            updates.append("processed_count = ?")
            params.append(processed_count)
        if failed_count is not None:
            updates.append("failed_count = ?")
            params.append(failed_count)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if export_path is not None:
            updates.append("export_path = ?")
            params.append(export_path)
        if completed_at is not None:
            updates.append("completed_at = ?")
            params.append(completed_at)

        if not updates:
            conn.close()
            return

        params.append(search_id)
        query = f"UPDATE search_history SET {', '.join(updates)} WHERE id = ?"
        conn.execute(query, params)
        conn.commit()
        conn.close()


class SearchRepository:
    """Repository for search history operations."""

    def __init__(self, db: DatabaseConnection):
        self.db = db

    def insert(self, **kwargs) -> int:
        return self.db.insert_search(**kwargs)

    def get_all(self) -> List[Dict[str, Any]]:
        conn = self.db.connect()
        cursor = conn.execute(SEARCH_SELECT_ALL)
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "id": row[0], "keyword": row[1], "location": row[2],
                "result_limit": row[3], "discovered_count": row[4],
                "processed_count": row[5], "failed_count": row[6],
                "status": row[7], "started_at": row[8],
                "completed_at": row[9], "export_path": row[10],
            }
            for row in rows
        ]

    def get_by_id(self, search_id: int) -> Optional[Dict[str, Any]]:
        conn = self.db.connect()
        cursor = conn.execute(SEARCH_SELECT_BY_ID, (search_id,))
        row = cursor.fetchone()
        conn.close()
        if row is None:
            return None
        return {
            "id": row[0], "keyword": row[1], "location": row[2],
            "result_limit": row[3], "discovered_count": row[4],
            "processed_count": row[5], "failed_count": row[6],
            "status": row[7], "started_at": row[8],
            "completed_at": row[9], "export_path": row[10],
        }