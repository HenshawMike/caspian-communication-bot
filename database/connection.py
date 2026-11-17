"""SQLite database connection and lifecycle manager."""

import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager
from agent.config import settings
from agent.logging_config import logger


class DatabaseManager:
    """Manages SQLite connections with WAL mode and foreign key enforcement."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.get_db_path()
        self._ensure_parent_dir()

    def _ensure_parent_dir(self) -> None:
        """Ensure parent directory of database exists."""
        if not self.db_path.parent.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Create and configure a SQLite connection."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=10.0,
        )
        conn.row_factory = sqlite3.Row
        # Enable write-ahead logging and foreign keys
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    @contextmanager
    def connection(self):
        """Context manager providing a safe transaction-managed connection."""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


db_manager = DatabaseManager()
