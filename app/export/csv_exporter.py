import csv
import os
import re
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
            filename = f"leads_{timestamp}.csv"

        filename = self._safe_filename(filename)
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

    @staticmethod
    def _safe_filename(filename: str) -> str:
        """Strip path separators and guarantee a .csv extension."""
        filename = os.path.basename(str(filename).strip()) or "leads.csv"
        filename = re.sub(r"[^\w.\- ]", "_", filename).strip()
        if not filename:
            filename = "leads.csv"
        if not filename.lower().endswith(".csv"):
            filename += ".csv"
        return filename

    def export_records(self, records: List[object], filename: str = None) -> str:
        """Export a list of business records to CSV."""
        export_records = []
        for record in records:
            if isinstance(record, dict):
                export_records.append(record)
            elif hasattr(record, "to_dict"):
                export_records.append(record.to_dict())
            elif hasattr(record, "__dict__"):
                export_records.append(dict(vars(record)))
            else:
                export_records.append({})

        return self.export(export_records, filename)