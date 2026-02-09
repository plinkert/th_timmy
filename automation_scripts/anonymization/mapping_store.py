"""
Mapping store – backend for original ↔ pseudonym mappings.

Stores (original, pseudonym) pairs. Used by DeterministicAnonymizer for deanonymization.
Implementations: InMemoryMappingStore (tests), SQLiteMappingStore (dev/prod).
"""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional

import logging

logger = logging.getLogger(__name__)


class MappingStore(ABC):
    """Abstract interface for mapping storage."""

    @abstractmethod
    def store(self, original: str, pseudonym: str, field_type: Optional[str] = None) -> None:
        """Store mapping original → pseudonym."""
        pass

    @abstractmethod
    def lookup_original(self, pseudonym: str) -> Optional[str]:
        """Lookup original value by pseudonym. Returns None if not found."""
        pass

    @abstractmethod
    def lookup_pseudonym(self, original: str) -> Optional[str]:
        """Lookup pseudonym by original value. Returns None if not found."""
        pass


class InMemoryMappingStore(MappingStore):
    """In-memory mapping store for tests."""

    def __init__(self) -> None:
        self._original_to_pseudonym: Dict[str, str] = {}
        self._pseudonym_to_original: Dict[str, str] = {}

    def store(self, original: str, pseudonym: str, field_type: Optional[str] = None) -> None:
        self._original_to_pseudonym[original] = pseudonym
        self._pseudonym_to_original[pseudonym] = original

    def lookup_original(self, pseudonym: str) -> Optional[str]:
        return self._pseudonym_to_original.get(pseudonym)

    def lookup_pseudonym(self, original: str) -> Optional[str]:
        return self._original_to_pseudonym.get(original)


class SQLiteMappingStore(MappingStore):
    """SQLite-backed mapping store. For dev; use encrypted storage in prod."""

    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS anonymization_mappings (
                original_value TEXT NOT NULL,
                pseudonym_value TEXT NOT NULL,
                field_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (original_value)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_pseudonym ON anonymization_mappings(pseudonym_value)
        """)
        conn.commit()

    def store(self, original: str, pseudonym: str, field_type: Optional[str] = None) -> None:
        conn = self._get_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO anonymization_mappings (original_value, pseudonym_value, field_type)
            VALUES (?, ?, ?)
            """,
            (original, pseudonym, field_type),
        )
        conn.commit()

    def lookup_original(self, pseudonym: str) -> Optional[str]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT original_value FROM anonymization_mappings WHERE pseudonym_value = ?",
            (pseudonym,),
        ).fetchone()
        return row["original_value"] if row else None

    def lookup_pseudonym(self, original: str) -> Optional[str]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT pseudonym_value FROM anonymization_mappings WHERE original_value = ?",
            (original,),
        ).fetchone()
        return row["pseudonym_value"] if row else None

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
