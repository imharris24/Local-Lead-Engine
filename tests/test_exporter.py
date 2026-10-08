import csv
from types import SimpleNamespace

from app.export.csv_exporter import CsvExporter


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


class TestCsvExporter:
    def test_export_writes_headers_and_rows(self, tmp_path):
        exporter = CsvExporter(export_path=str(tmp_path))
        path = exporter.export(
            [
                {
                    "name": "ABC Dental",
                    "category": "Dentist",
                    "address": "Gulberg, Lahore",
                    "phone": "+923001234567",
                    "website": "https://example.com",
                    "rating": 4.7,
                    "review_count": 183,
                    "maps_url": "https://...",
                }
            ],
            "dentists_lahore.csv",
        )
        rows = read_csv(path)
        assert rows[0] == CsvExporter.DEFAULT_HEADERS
        assert rows[1][0] == "ABC Dental"
        assert rows[1][5] == "4.7"

    def test_export_adds_csv_extension(self, tmp_path):
        exporter = CsvExporter(export_path=str(tmp_path))
        path = exporter.export([{"name": "X"}], "dentists_lahore")
        assert path.endswith(".csv")

    def test_export_sanitizes_path_separators(self, tmp_path):
        exporter = CsvExporter(export_path=str(tmp_path))
        path = exporter.export([{"name": "X"}], "../../evil.csv")
        assert ".." not in path.replace(str(tmp_path), "")

    def test_export_handles_none_values(self, tmp_path):
        exporter = CsvExporter(export_path=str(tmp_path))
        path = exporter.export([{"name": "No Phone", "phone": None}], "none.csv")
        rows = read_csv(path)
        assert rows[1][3] == ""

    def test_export_records_accepts_objects(self, tmp_path):
        exporter = CsvExporter(export_path=str(tmp_path))
        record = SimpleNamespace(
            name="Obj Dental",
            category="Dentist",
            address="DHA, Lahore",
            phone=None,
            website=None,
            rating=4.2,
            review_count=87,
            maps_url="https://maps.example",
        )
        path = exporter.export_records([record], "objects")
        rows = read_csv(path)
        assert rows[1][0] == "Obj Dental"
        assert rows[1][6] == "87"

    def test_export_records_accepts_records_with_to_dict(self, tmp_path):
        class Rec:
            def to_dict(self):
                return {"name": "Dicty", "phone": "0300"}

        exporter = CsvExporter(export_path=str(tmp_path))
        path = exporter.export_records([Rec()], "todict")
        rows = read_csv(path)
        assert rows[1][0] == "Dicty"
        assert rows[1][3] == "0300"

    def test_default_filename_is_timestamped(self, tmp_path):
        exporter = CsvExporter(export_path=str(tmp_path))
        path = exporter.export([{"name": "X"}])
        name = path.split("/")[-1].split("\\")[-1]
        assert name.startswith("leads_") and name.endswith(".csv")
