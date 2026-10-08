#!/usr/bin/env python3
"""Main entry point for the Local Lead Engine."""

import argparse
import sys
from datetime import datetime, timezone

from app.config import settings
from app.database.connection import DatabaseConnection
from app.database.repository import BusinessRepository
from app.scraper.browser import BrowserEngine
from app.scraper.search import SearchConfig, SearchEngine
from app.export.csv_exporter import CsvExporter
from app.logging import logger


def setup_database() -> BusinessRepository:
    """Initialize database and return repository."""
    db = DatabaseConnection(str(settings.database_path))
    repo = BusinessRepository(db)
    repo.initialize()
    return repo


def run_search(
    keyword: str,
    location: str,
    limit: int = settings.default_limit,
    headless: bool = settings.headless,
) -> None:
    """Run a single search job."""
    config = SearchConfig(keyword=keyword, location=location, limit=limit)

    print_banner(config)

    repo = setup_database()
    search_engine = SearchEngine(config, repo)

    search_id = repo.insert_search(
        keyword=config.keyword,
        location=config.location,
        result_limit=config.limit,
    )

    browser = BrowserEngine(headless=headless)
    export_path = None
    status = "completed"
    try:
        logger.info("Starting browser...")
        browser.start()
        page = browser.new_page()

        search_engine.run(page)

        # Export to CSV
        export_path = export_results(search_engine, config, repo)
        print_summary(search_engine, export_path)

    except Exception as e:
        status = "failed"
        logger.error(f"Search job failed: {e}")
        print_summary(search_engine, None)
    finally:
        repo.update_search(
            search_id,
            discovered_count=search_engine.discovered,
            processed_count=search_engine.processed,
            failed_count=search_engine.errors,
            status=status,
            export_path=export_path,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        browser.close()

    logger.info("Job complete")


def export_results(search_engine: SearchEngine, config: SearchConfig, repo) -> str:
    """Export this job's businesses (falling back to everything) to CSV."""
    records = repo.get_by_search(config.keyword, config.location)
    if not records:
        records = repo.get_all()
    if not records:
        logger.warning("No records available to export")
        return None

    exporter = CsvExporter(export_path=str(settings.export_path))
    filepath = exporter.export_records(records, config.slug)
    logger.info(f"Exported {len(records)} records to {filepath}")
    return filepath


def print_banner(config: SearchConfig) -> None:
    print("Local Lead Engine")
    print("────────────────────────────────────────")
    print()
    print(f"Keyword:    {config.keyword}")
    print(f"Location:   {config.location}")
    print(f"Limit:      {config.limit}")
    print()


def print_summary(search_engine: SearchEngine, export_path: str) -> None:
    stats = search_engine.to_dict()
    print()
    print(f"Discovered: {stats['discovered']}")
    print(f"Processed:  {stats['processed']}")
    print(f"New:        {stats['new']}")
    print(f"Duplicates: {stats['duplicates']}")
    print(f"Errors:     {stats['errors']}")
    print()
    if export_path:
        print("Export complete.")
        print()
        print("File:")
        print(export_path)
    else:
        print("Export skipped (no records).")
    print()


def main() -> None:
    """Main CLI entry point."""
    # Windows terminals default to cp1252, which cannot encode the
    # progress/banner characters or many international business names.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

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
        action=argparse.BooleanOptionalAction,
        default=settings.headless,
        help="Run browser in headless mode (default: {})".format(settings.headless),
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
