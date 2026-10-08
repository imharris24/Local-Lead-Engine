import csv
from pathlib import Path
from typing import List, Dict, Any, Optional


class CsvExporter:
    """Exports business records to CSV format."""

    DEFAULT_HEADERS = [
        "name",
        "category",
        "address",
        "phone",
        "website",
        "rating",
        "review_count",
        "maps_url",
    ]

    def __init__(self, export_path: str = "data/exports", headers: List[str] = None):
        self.export_path = Path(export_path)
        self.export_path.mkdir(parents=True, exist_ok=True)
        self.headers = headers or self.DEFAULT_HEADERS

    def export(self, records: List[Dict[str, Any]], filename: str = None) -> str:
        """Export records to CSV file."""
        self.export_path.mkdir(parents=True, exist_ok=True)

        if filename is None:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename}_{timestamp}.csv" if filename else f"leads_{timestamp}.csv"

        filepath = self.export_path / filename

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(self.headers)

            for record in records:
                row = []
                for header in self.headers:
                    value = record.get(header, "")
                    if value is None:
                        value = ""
                    row.append(value)
                writer.writerow(row)

        return str(filepath)

    def export_records(self, records: List[object], filename: str = None) -> str:
        """Export a list of business records to CSV."""
        export_records = []
        for record in records:
            if hasattr(record, 'to_dict'):
                export_records.append(record.to_dict())
            elif isinstance(record, dict):
                export_records.append(record)
            else:
                # Try to convert to dict
                export_records.append({})

        return self.export(export_records, filename)