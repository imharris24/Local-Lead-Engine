import sqlite3
from pathlib import Path
from typing import Optional, ContextManager

BASE_DIR = Path(__file__).parent.parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "database" / "leads.db"


class DatabaseConnection:
    def __init__(self, db_path: str = str(DEFAULT_DB_PATH)):
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.db_path)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA foreign_keys=ON")
        return self._connection

    def close(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None

    def __enter__(self) -> sqlite3.Connection:
        return self.connect()

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[object],
    ) -> None:
        self.close()

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            return self.connect()
        return self._connection