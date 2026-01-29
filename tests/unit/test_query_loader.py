"""Unit tests for query_loader (Step 1.1)."""

from pathlib import Path

import pytest

from automation_scripts.playbooks.query_loader import (
    load_queries,
    QueryEntry,
    QueryLoadError,
)


def test_load_queries_success(tmp_path):
    """Load queries from valid playbook."""
    (tmp_path / "metadata.yml").write_text("""
technique_description: "Test"
data_sources:
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk.sql"
  - tool: "elk"
    mode: "API"
    query_path: "queries/elk_api.json"
""")
    (tmp_path / "queries").mkdir()
    (tmp_path / "queries" / "elk.sql").write_text("SELECT * FROM events;")
    (tmp_path / "queries" / "elk_api.json").write_text('{"query": {}}')

    entries = load_queries(tmp_path)
    assert len(entries) == 2
    assert entries[0].tool == "elk"
    assert entries[0].mode == "manual"
    assert entries[0].content == "SELECT * FROM events;"
    assert entries[1].tool == "elk"
    assert entries[1].mode == "API"
    assert "query" in entries[1].content


def test_load_queries_with_metadata(tmp_path):
    """Load queries with pre-loaded metadata."""
    (tmp_path / "queries").mkdir()
    (tmp_path / "queries" / "test.kql").write_text("DeviceProcessEvents | take 10")
    metadata = {
        "technique_description": "Test",
        "data_sources": [
            {"tool": "ms_defender", "mode": "manual", "query_path": "queries/test.kql"},
        ],
    }
    entries = load_queries(tmp_path, metadata=metadata)
    assert len(entries) == 1
    assert entries[0].tool == "ms_defender"
    assert entries[0].content == "DeviceProcessEvents | take 10"


def test_load_queries_missing_file(tmp_path):
    """Missing query file raises QueryLoadError."""
    (tmp_path / "metadata.yml").write_text("""
technique_description: "Test"
data_sources:
  - tool: "elk"
    mode: "manual"
    query_path: "queries/nonexistent.sql"
""")
    with pytest.raises(QueryLoadError) as exc_info:
        load_queries(tmp_path)
    assert "nonexistent" in str(exc_info.value) or "not found" in str(exc_info.value)


def test_load_queries_empty_data_sources(tmp_path):
    """Empty data_sources raises QueryLoadError."""
    (tmp_path / "metadata.yml").write_text("""
technique_description: "Test"
data_sources: []
""")
    with pytest.raises(QueryLoadError) as exc_info:
        load_queries(tmp_path)
    assert "data_sources" in str(exc_info.value)


def test_load_queries_path_traversal_blocked(tmp_path):
    """query_path escaping playbook dir raises QueryLoadError."""
    (tmp_path / "metadata.yml").write_text("""
technique_description: "Test"
data_sources:
  - tool: "elk"
    mode: "manual"
    query_path: "../../../etc/passwd"
""")
    with pytest.raises(QueryLoadError) as exc_info:
        load_queries(tmp_path)
    assert "escape" in str(exc_info.value) or "not found" in str(exc_info.value)
