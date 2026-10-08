#!/usr/bin/env python3
"""Main entry point for the Local Lead Engine."""

import argparse
import sys
from pathlib import Path

from app.config import settings
from app.database.connection import DatabaseConnection
from app.database.repository import BusinessRepository, SearchRepository
from app.scraper.browser import BrowserEngine
from app.scraper.search import SearchConfig, SearchEngine
from app.scraper.business import Business
from app.export.csv_exporter import CsvExporter
from app.logging import logger


def setup_database() -> BusinessRepository:
    """Initialize database and return repository."""
    db = DatabaseConnection(str(settings.database_path))
    repo = BusinessRepository(db)
    repo.initialize()
    return repo


def setup_search_engine(config: SearchConfig, repo: BusinessRepository) -> SearchEngine:
    """Create a search engine instance."""
    search_engine = SearchEngine(config, repo)
    return search_engine


def run_search(
    keyword: str,
    location: str,
    limit: int = settings.default_limit,
    headless: bool = settings.headless,
) -> None:
    """Run a single search job."""
    logger.info(f"Starting job: {keyword} in {location}")

    config = SearchConfig(keyword=keyword, location=location, limit=limit)
    search_engine = setup_search_engine(config, None)

    # Record search in database
    db = DatabaseConnection(str(settings.database_path))
    repo = BusinessRepository(db)
    repo.initialize()
    search_id = repo.insert_search(
        keyword=config.keyword,
        location=config.location,
        result_limit=config.limit,
    )

    # Run browser search
    browser = BrowserEngine(headless=headless)
    try:
        browser.start()
        page = browser.new_page()

        # Navigate to search
        search_url = _build_search_url(config)
        logger.info(f"Navigating to search: {search_url}")
        page.goto(search_url)

        # Wait for results to load
        page.wait_for_load_state("networkidle")

        # Discover businesses
        discovered = _discover_businesses(page, search_engine, limit)

        logger.info(f"Discovered {discovered} businesses")

        # Update search record
        repo.update_search(
            search_id,
            discovered_count=discovered,
            processed_count=search_engine.processed,
            failed_count=search_engine.errors,
            status="completed",
        )

        # Export to CSV
        _export_results(search_engine, config, repo)

    except Exception as e:
        logger.error(f"Search job failed: {e}")
        if 'search_id' in locals():
            repo.update_search(
                search_id,
                failed_count=search_engine.errors + 1,
                status="failed",
            )
    finally:
        browser.close()

    logger.info("Job complete")


def _build_search_url(config: SearchConfig) -> str:
    """Build the search URL for the given configuration."""
    from urllib.parse import quote_plus
    base = "https://www.google.com/maps/search/"
    query = f"{quote_plus(config.keyword)}+{quote_plus(config.location)}"
    return f"{base}{query}?gl=country-pk"


def _discover_businesses(page, search_engine: SearchEngine, limit: int) -> int:
    """Discover businesses from the search page."""
    # This is a simplified discovery - in production would extract business cards
    search_engine.discovered = limit
    return limit


def _export_results(search_engine: SearchEngine, config: SearchConfig, repo) -> None:
    """Export search results to CSV."""
    repo_db = repo if hasattr(repo, 'export') else None
    exporter = CsvExporter(export_path=str(settings.export_path))
    # Get records from database
    records = repo_db.get_all() if hasattr(repo_db, 'get_all') else []
    if records:
        filename = f"{config.keyword}_{config.location}"
        filepath = exporter.export(records, filename)
        logger.info(f"Exported {len(records)} records to {filepath}")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Local Lead Engine - Lead generation tool"
    )
    parser.add_argument(
        "--keyword",
        type=str,
        required=True,
        help="Search keyword (e.g., 'dentists')",
    )
    parser.add_argument(
        "--location",
        type=str,
        required=True,
        help="Location/city (e.g., 'Lahore')",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=settings.default_limit,
        help="Maximum number of results (default: {})".format(settings.default_limit),
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode",
    )

    args = parser.parse_args()

    run_search(
        keyword=args.keyword,
        location=args.location,
        limit=args.limit,
        headless=args.headless,
    )


if __name__ == "__main__":
    main()