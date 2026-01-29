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


def test_load_queries_with_tool_class(tmp_path):
    """Load queries with tool_class in data_sources returns QueryEntry with tool_class."""
    (tmp_path / "metadata.yml").write_text("""
technique_description: "Test"
data_sources:
  - tool_class: "siem"
    tool: "elk"
    mode: "manual"
    query_path: "queries/elk.sql"
  - tool_class: "edr"
    tool: "ms_defender"
    mode: "API"
    query_path: "queries/ms_api.json"
""")
    (tmp_path / "queries").mkdir()
    (tmp_path / "queries" / "elk.sql").write_text("SELECT 1")
    (tmp_path / "queries" / "ms_api.json").write_text('{"Query": "DeviceEvents"}')
    entries = load_queries(tmp_path)
    assert len(entries) == 2
    assert entries[0].tool_class == "siem"
    assert entries[0].tool == "elk"
    assert entries[1].tool_class == "edr"
    assert entries[1].tool == "ms_defender"


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


# --- YAML format tests ---

def test_load_queries_yaml_with_query_id(tmp_path):
    """Load queries from YAML file with query_id."""
    (tmp_path / "metadata.yml").write_text("""
technique_description: "Test"
data_sources:
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk.yml"
    query_id: memory_ops
  - tool: "elk"
    mode: "API"
    query_path: "queries/elk.yml"
    query_id: memory_ops
""")
    (tmp_path / "queries").mkdir()
    (tmp_path / "queries" / "elk.yml").write_text("""
manual:
  memory_ops:
    sql: "SELECT * FROM events WHERE timestamp >= NOW() - INTERVAL '7 days'"
api:
  memory_ops:
    body:
      query:
        range: { "@timestamp": { "gte": "now-7d", "lte": "now" } }
""")
    entries = load_queries(tmp_path)
    assert len(entries) == 2
    assert entries[0].tool == "elk"
    assert entries[0].mode == "manual"
    assert entries[0].query_id == "memory_ops"
    assert "INTERVAL" in entries[0].content
    assert entries[1].tool == "elk"
    assert entries[1].mode == "API"
    assert entries[1].query_id == "memory_ops"
    assert "now-7d" in entries[1].content


def test_load_queries_yaml_with_query_ids(tmp_path):
    """Load queries from YAML file with query_ids (multiple entries)."""
    (tmp_path / "metadata.yml").write_text("""
technique_description: "Test"
data_sources:
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk.yml"
    query_ids: [q1, q2]
""")
    (tmp_path / "queries").mkdir()
    (tmp_path / "queries" / "elk.yml").write_text("""
manual:
  q1:
    sql: "SELECT 1"
  q2:
    sql: "SELECT 2"
""")
    entries = load_queries(tmp_path)
    assert len(entries) == 2
    assert entries[0].query_id == "q1"
    assert entries[0].content == "SELECT 1"
    assert entries[1].query_id == "q2"
    assert entries[1].content == "SELECT 2"


def test_load_queries_yaml_ms_defender(tmp_path):
    """Load ms_defender queries from YAML (kql for manual, body for api)."""
    (tmp_path / "metadata.yml").write_text("""
technique_description: "Test"
data_sources:
  - tool: "ms_defender"
    mode: "manual"
    query_path: "queries/ms_defender.yml"
    query_id: hunt
  - tool: "ms_defender"
    mode: "API"
    query_path: "queries/ms_defender.yml"
    query_id: hunt
""")
    (tmp_path / "queries").mkdir()
    (tmp_path / "queries" / "ms_defender.yml").write_text("""
manual:
  hunt:
    kql: "DeviceEvents | where Timestamp > ago(7d)"
api:
  hunt:
    body:
      Query: "DeviceEvents | where Timestamp > ago(7d)"
""")
    entries = load_queries(tmp_path)
    assert len(entries) == 2
    assert entries[0].content == "DeviceEvents | where Timestamp > ago(7d)"
    assert "ago(7d)" in entries[1].content or "DeviceEvents" in entries[1].content


def test_load_queries_yaml_missing_query_id(tmp_path):
    """YAML query_path without query_id/query_ids raises QueryLoadError."""
    (tmp_path / "metadata.yml").write_text("""
technique_description: "Test"
data_sources:
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk.yml"
""")
    (tmp_path / "queries").mkdir()
    (tmp_path / "queries" / "elk.yml").write_text("manual:\n  q1:\n    sql: 'SELECT 1'\napi:\n  q1:\n    body: {}")
    with pytest.raises(QueryLoadError) as exc_info:
        load_queries(tmp_path)
    assert "query_id" in str(exc_info.value) or "query_ids" in str(exc_info.value)


def test_load_queries_yaml_query_id_not_found(tmp_path):
    """YAML with query_id not in file raises QueryLoadError."""
    (tmp_path / "metadata.yml").write_text("""
technique_description: "Test"
data_sources:
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk.yml"
    query_id: nonexistent
""")
    (tmp_path / "queries").mkdir()
    (tmp_path / "queries" / "elk.yml").write_text("manual:\n  q1:\n    sql: 'SELECT 1'\napi:\n  q1:\n    body: {}")
    with pytest.raises(QueryLoadError) as exc_info:
        load_queries(tmp_path)
    assert "nonexistent" in str(exc_info.value) or "not found" in str(exc_info.value)
