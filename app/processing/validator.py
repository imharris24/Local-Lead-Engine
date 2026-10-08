from typing import List, Optional


class BusinessValidator:
    """Validates business records for completeness and consistency."""

    @staticmethod
    def validate_record(record: object) -> bool:
        """Validate that a record has required minimum fields."""
        if not hasattr(record, 'name'):
            return False

        name = getattr(record, 'name', None)
        if not name or str(name).strip() == "":
            return False

        return True

    @staticmethod
    def validate_batch(records: List[object]) -> List[object]:
        """Validate a batch of records, returning only valid ones."""
        return [r for r in records if BusinessValidator.validate_record(r)]