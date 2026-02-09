"""Unit tests for anonymization.mapping_store (Step 1.3)."""

import tempfile
from pathlib import Path

import pytest

from automation_scripts.anonymization.mapping_store import (
    InMemoryMappingStore,
    MappingStore,
    SQLiteMappingStore,
)


def test_in_memory_store_store_and_lookup():
    store = InMemoryMappingStore()
    store.store("192.168.1.100", "a1b2c3d4", "ip_address")
    assert store.lookup_pseudonym("192.168.1.100") == "a1b2c3d4"
    assert store.lookup_original("a1b2c3d4") == "192.168.1.100"


def test_in_memory_store_lookup_missing():
    store = InMemoryMappingStore()
    assert store.lookup_pseudonym("unknown") is None
    assert store.lookup_original("unknown") is None


def test_in_memory_store_overwrite():
    store = InMemoryMappingStore()
    store.store("x", "p1", None)
    store.store("x", "p2", None)
    assert store.lookup_pseudonym("x") == "p2"
    assert store.lookup_original("p1") is None
    assert store.lookup_original("p2") == "x"


def test_sqlite_store_store_and_lookup(tmp_path):
    db = tmp_path / "mappings.db"
    store = SQLiteMappingStore(db)
    store.store("user@example.com", "hash123", "email")
    assert store.lookup_pseudonym("user@example.com") == "hash123"
    assert store.lookup_original("hash123") == "user@example.com"
    store.close()


def test_sqlite_store_persists(tmp_path):
    db = tmp_path / "mappings.db"
    s1 = SQLiteMappingStore(db)
    s1.store("192.168.1.1", "pseudo1", "ip")
    s1.close()
    s2 = SQLiteMappingStore(db)
    assert s2.lookup_original("pseudo1") == "192.168.1.1"
    assert s2.lookup_pseudonym("192.168.1.1") == "pseudo1"
    s2.close()


def test_sqlite_store_insert_or_replace(tmp_path):
    db = tmp_path / "mappings.db"
    store = SQLiteMappingStore(db)
    store.store("key", "v1", None)
    store.store("key", "v2", None)
    assert store.lookup_pseudonym("key") == "v2"
    assert store.lookup_original("v1") is None
    assert store.lookup_original("v2") == "key"
    store.close()
