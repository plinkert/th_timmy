"""Unit tests for playbook_validator (Step 1.1)."""

from pathlib import Path

import pytest

from automation_scripts.playbooks.playbook_validator import (
    validate_playbook,
    ValidationResult,
)

# Minimal valid metadata with all required fields (5+ queries, hunting_indicators, TP/FP)
VALID_METADATA = """
name: "Test Playbook"
technique_description: "Test technique description for report intro."
hunting_indicators: "Key indicators to search for."
true_positive_conditions: "When to treat as True Positive."
false_positive_conditions: "When to treat as False Positive."
data_sources:
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk.sql"
  - tool: "elk"
    mode: "API"
    query_path: "queries/elk_api.json"
  - tool: "ms_defender"
    mode: "manual"
    query_path: "queries/ms_defender.kql"
  - tool: "ms_defender"
    mode: "API"
    query_path: "queries/ms_defender_api.json"
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk_02.sql"
"""


def test_validate_playbook_valid(tmp_path):
    """Valid playbook with all required fields passes."""
    (tmp_path / "metadata.yml").write_text(VALID_METADATA)
    result = validate_playbook(tmp_path, validate_placeholders=False)
    assert result.success is True
    assert result.errors == []


def test_validate_playbook_missing_technique_description(tmp_path):
    """Playbook without technique_description fails."""
    (tmp_path / "metadata.yml").write_text("""
name: "Test"
hunting_indicators: "Indicators."
true_positive_conditions: "TP."
false_positive_conditions: "FP."
data_sources:
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk.sql"
  - tool: "elk"
    mode: "API"
    query_path: "queries/elk_api.json"
  - tool: "ms_defender"
    mode: "manual"
    query_path: "queries/ms.kql"
  - tool: "ms_defender"
    mode: "API"
    query_path: "queries/ms_api.json"
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk_02.sql"
""")
    result = validate_playbook(tmp_path, validate_placeholders=False)
    assert result.success is False
    assert any("technique_description" in e for e in result.errors)


def test_validate_playbook_empty_technique_description(tmp_path):
    """Playbook with empty technique_description fails."""
    (tmp_path / "metadata.yml").write_text("""
name: "Test"
technique_description: ""
hunting_indicators: "Indicators."
true_positive_conditions: "TP."
false_positive_conditions: "FP."
data_sources:
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk.sql"
  - tool: "elk"
    mode: "API"
    query_path: "queries/elk_api.json"
  - tool: "ms_defender"
    mode: "manual"
    query_path: "queries/ms.kql"
  - tool: "ms_defender"
    mode: "API"
    query_path: "queries/ms_api.json"
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk_02.sql"
""")
    result = validate_playbook(tmp_path, validate_placeholders=False)
    assert result.success is False
    assert any("technique_description" in e for e in result.errors)


def test_validate_playbook_missing_data_sources(tmp_path):
    """Playbook without data_sources fails."""
    (tmp_path / "metadata.yml").write_text("""
name: "Test"
technique_description: "Valid description."
hunting_indicators: "Indicators."
true_positive_conditions: "TP."
false_positive_conditions: "FP."
""")
    result = validate_playbook(tmp_path, validate_placeholders=False)
    assert result.success is False
    assert any("data_sources" in e for e in result.errors)


def test_validate_playbook_empty_data_sources(tmp_path):
    """Playbook with empty data_sources list fails."""
    (tmp_path / "metadata.yml").write_text("""
name: "Test"
technique_description: "Valid description."
hunting_indicators: "Indicators."
true_positive_conditions: "TP."
false_positive_conditions: "FP."
data_sources: []
""")
    result = validate_playbook(tmp_path, validate_placeholders=False)
    assert result.success is False
    assert any("at least" in e for e in result.errors)


def test_validate_playbook_fewer_than_5_queries(tmp_path):
    """Playbook with fewer than 5 queries fails."""
    (tmp_path / "metadata.yml").write_text("""
name: "Test"
technique_description: "Valid description."
hunting_indicators: "Indicators."
true_positive_conditions: "TP."
false_positive_conditions: "FP."
data_sources:
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk.sql"
  - tool: "ms_defender"
    mode: "API"
    query_path: "queries/ms_api.json"
""")
    result = validate_playbook(tmp_path, validate_placeholders=False)
    assert result.success is False
    assert any("5" in e for e in result.errors)


def test_validate_playbook_missing_hunting_indicators(tmp_path):
    """Playbook without hunting_indicators fails."""
    (tmp_path / "metadata.yml").write_text("""
name: "Test"
technique_description: "Valid."
true_positive_conditions: "TP."
false_positive_conditions: "FP."
data_sources:
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk.sql"
  - tool: "elk"
    mode: "API"
    query_path: "queries/elk_api.json"
  - tool: "ms_defender"
    mode: "manual"
    query_path: "queries/ms.kql"
  - tool: "ms_defender"
    mode: "API"
    query_path: "queries/ms_api.json"
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk_02.sql"
""")
    result = validate_playbook(tmp_path, validate_placeholders=False)
    assert result.success is False
    assert any("hunting_indicators" in e for e in result.errors)


def test_validate_playbook_missing_true_positive_conditions(tmp_path):
    """Playbook without true_positive_conditions fails."""
    (tmp_path / "metadata.yml").write_text("""
name: "Test"
technique_description: "Valid."
hunting_indicators: "Indicators."
false_positive_conditions: "FP."
data_sources:
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk.sql"
  - tool: "elk"
    mode: "API"
    query_path: "queries/elk_api.json"
  - tool: "ms_defender"
    mode: "manual"
    query_path: "queries/ms.kql"
  - tool: "ms_defender"
    mode: "API"
    query_path: "queries/ms_api.json"
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk_02.sql"
""")
    result = validate_playbook(tmp_path, validate_placeholders=False)
    assert result.success is False
    assert any("true_positive" in e for e in result.errors)


def test_validate_playbook_missing_false_positive_conditions(tmp_path):
    """Playbook without false_positive_conditions fails."""
    (tmp_path / "metadata.yml").write_text("""
name: "Test"
technique_description: "Valid."
hunting_indicators: "Indicators."
true_positive_conditions: "TP."
data_sources:
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk.sql"
  - tool: "elk"
    mode: "API"
    query_path: "queries/elk_api.json"
  - tool: "ms_defender"
    mode: "manual"
    query_path: "queries/ms.kql"
  - tool: "ms_defender"
    mode: "API"
    query_path: "queries/ms_api.json"
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk_02.sql"
""")
    result = validate_playbook(tmp_path, validate_placeholders=False)
    assert result.success is False
    assert any("false_positive" in e for e in result.errors)


def test_validate_playbook_invalid_mode(tmp_path):
    """Playbook with invalid mode (not manual/API) fails."""
    (tmp_path / "metadata.yml").write_text("""
name: "Test"
technique_description: "Valid description."
hunting_indicators: "Indicators."
true_positive_conditions: "TP."
false_positive_conditions: "FP."
data_sources:
  - tool: "elk"
    mode: "automatic"
    query_path: "queries/elk.sql"
  - tool: "elk"
    mode: "API"
    query_path: "queries/elk_api.json"
  - tool: "ms_defender"
    mode: "manual"
    query_path: "queries/ms.kql"
  - tool: "ms_defender"
    mode: "API"
    query_path: "queries/ms_api.json"
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk_02.sql"
""")
    result = validate_playbook(tmp_path, validate_placeholders=False)
    assert result.success is False
    assert any("manual" in e or "API" in e for e in result.errors)


def test_validate_playbook_missing_tool(tmp_path):
    """Playbook with missing tool in data_sources entry fails."""
    (tmp_path / "metadata.yml").write_text("""
name: "Test"
technique_description: "Valid description."
hunting_indicators: "Indicators."
true_positive_conditions: "TP."
false_positive_conditions: "FP."
data_sources:
  - mode: "manual"
    query_path: "queries/elk.sql"
  - tool: "elk"
    mode: "API"
    query_path: "queries/elk_api.json"
  - tool: "ms_defender"
    mode: "manual"
    query_path: "queries/ms.kql"
  - tool: "ms_defender"
    mode: "API"
    query_path: "queries/ms_api.json"
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk_02.sql"
""")
    result = validate_playbook(tmp_path, validate_placeholders=False)
    assert result.success is False
    assert any("tool" in e for e in result.errors)


def test_validate_playbook_missing_query_path(tmp_path):
    """Playbook with missing query_path in data_sources entry fails."""
    (tmp_path / "metadata.yml").write_text("""
name: "Test"
technique_description: "Valid description."
hunting_indicators: "Indicators."
true_positive_conditions: "TP."
false_positive_conditions: "FP."
data_sources:
  - tool: "elk"
    mode: "manual"
  - tool: "elk"
    mode: "API"
    query_path: "queries/elk_api.json"
  - tool: "ms_defender"
    mode: "manual"
    query_path: "queries/ms.kql"
  - tool: "ms_defender"
    mode: "API"
    query_path: "queries/ms_api.json"
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk_02.sql"
""")
    result = validate_playbook(tmp_path, validate_placeholders=False)
    assert result.success is False
    assert any("query_path" in e for e in result.errors)


def test_validate_playbook_nonexistent_dir():
    """Playbook with nonexistent directory fails."""
    result = validate_playbook("/nonexistent/playbook/dir", validate_placeholders=False)
    assert result.success is False
    assert len(result.errors) >= 1


def test_validate_playbook_with_schema(tmp_path):
    """Valid playbook passes with custom schema path."""
    (tmp_path / "metadata.yml").write_text(VALID_METADATA)
    schema_dir = Path(__file__).resolve().parent.parent.parent / "configs" / "schemas"
    schema_path = schema_dir / "playbook_metadata.json"
    if schema_path.exists():
        result = validate_playbook(tmp_path, schema_path=schema_path, validate_placeholders=False)
        assert result.success is True


# --- Relative time validation tests ---


def test_validate_playbook_relative_time_passes(tmp_path):
    """Playbook with query files using relative time (ago(7d), now-7d) passes with no warnings."""
    (tmp_path / "metadata.yml").write_text(VALID_METADATA)
    (tmp_path / "queries").mkdir()
    (tmp_path / "queries" / "elk.sql").write_text(
        "SELECT * FROM events WHERE timestamp >= NOW() - INTERVAL '7 days'"
    )
    (tmp_path / "queries" / "elk_api.json").write_text(
        '{"query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-7d", "lte": "now"}}}]}}}'
    )
    (tmp_path / "queries" / "ms_defender.kql").write_text(
        "DeviceEvents | where Timestamp > ago(7d)"
    )
    (tmp_path / "queries" / "ms_defender_api.json").write_text(
        '{"Query": "DeviceEvents | where Timestamp > ago(7d)"}'
    )
    (tmp_path / "queries" / "elk_02.sql").write_text(
        "SELECT * FROM events WHERE timestamp >= NOW() - INTERVAL '7 days'"
    )
    result = validate_playbook(tmp_path)
    assert result.success is True
    assert not any("absolute" in w or "relative" in w for w in result.warnings)


def test_validate_playbook_absolute_time_warning(tmp_path):
    """Playbook with query file using absolute placeholders returns success with warnings."""
    (tmp_path / "metadata.yml").write_text(VALID_METADATA)
    (tmp_path / "queries").mkdir()
    (tmp_path / "queries" / "elk.sql").write_text(
        "SELECT * FROM events WHERE timestamp >= '{{timestamp_start}}' AND timestamp <= '{{timestamp_end}}'"
    )
    (tmp_path / "queries" / "elk_api.json").write_text(
        '{"query": {"bool": {"filter": []}}}'
    )
    (tmp_path / "queries" / "ms_defender.kql").write_text(
        "DeviceEvents | where Timestamp > ago(7d)"
    )
    (tmp_path / "queries" / "ms_defender_api.json").write_text(
        '{"Query": "DeviceEvents | where Timestamp > ago(7d)"}'
    )
    (tmp_path / "queries" / "elk_02.sql").write_text(
        "SELECT * FROM events WHERE timestamp >= NOW() - INTERVAL '7 days'"
    )
    result = validate_playbook(tmp_path)
    assert result.success is True
    assert any("relative" in w or "absolute" in w for w in result.warnings)


def test_validate_playbook_placeholders_disabled(tmp_path):
    """With validate_placeholders=False, no time validation warnings are generated."""
    (tmp_path / "metadata.yml").write_text(VALID_METADATA)
    (tmp_path / "queries").mkdir()
    (tmp_path / "queries" / "elk.sql").write_text(
        "SELECT * FROM events WHERE timestamp >= '{{timestamp_start}}'"
    )
    (tmp_path / "queries" / "elk_api.json").write_text('{"query": {}}')
    (tmp_path / "queries" / "ms_defender.kql").write_text("DeviceEvents")
    (tmp_path / "queries" / "ms_defender_api.json").write_text('{"Query": "DeviceEvents"}')
    (tmp_path / "queries" / "elk_02.sql").write_text("SELECT 1")
    result = validate_playbook(tmp_path, validate_placeholders=False)
    assert result.success is True
    assert result.warnings == []


def test_validate_playbook_tool_class_valid(tmp_path):
    """Playbook with valid tool_class (siem, edr, data_lake) passes."""
    (tmp_path / "metadata.yml").write_text(VALID_METADATA.replace(
        "  - tool: \"elk\"\n    mode: \"manual\"\n    query_path: \"queries/elk.sql\"",
        "  - tool_class: \"siem\"\n    tool: \"elk\"\n    mode: \"manual\"\n    query_path: \"queries/elk.sql\""
    ).replace(
        "  - tool: \"elk\"\n    mode: \"API\"\n    query_path: \"queries/elk_api.json\"",
        "  - tool_class: \"siem\"\n    tool: \"elk\"\n    mode: \"API\"\n    query_path: \"queries/elk_api.json\""
    ))
    (tmp_path / "queries").mkdir()
    for f in ["elk.sql", "elk_api.json", "ms_defender.kql", "ms_defender_api.json", "elk_02.sql"]:
        (tmp_path / "queries" / f).write_text("SELECT 1" if f.endswith(".sql") else "{}" if "api" in f else "DeviceEvents")
    result = validate_playbook(tmp_path, validate_placeholders=False)
    assert result.success is True
    assert result.errors == []


def test_validate_playbook_tool_class_invalid(tmp_path):
    """Playbook with invalid tool_class fails."""
    (tmp_path / "metadata.yml").write_text(VALID_METADATA.replace(
        "  - tool: \"elk\"\n    mode: \"manual\"\n    query_path: \"queries/elk.sql\"",
        "  - tool_class: \"invalid\"\n    tool: \"elk\"\n    mode: \"manual\"\n    query_path: \"queries/elk.sql\""
    ))
    (tmp_path / "queries").mkdir()
    for f in ["elk.sql", "elk_api.json", "ms_defender.kql", "ms_defender_api.json", "elk_02.sql"]:
        (tmp_path / "queries" / f).write_text("SELECT 1" if f.endswith(".sql") else "{}" if "api" in f else "DeviceEvents")
    result = validate_playbook(tmp_path, validate_placeholders=False)
    assert result.success is False
    assert any("tool_class" in e or "siem" in e or "edr" in e for e in result.errors)


def test_validate_playbook_query_file_not_found(tmp_path):
    """Playbook with missing query file generates warning."""
    (tmp_path / "metadata.yml").write_text(VALID_METADATA.replace(
        "queries/elk.sql", "queries/nonexistent.sql"
    ))
    (tmp_path / "queries").mkdir()
    (tmp_path / "queries" / "elk_api.json").write_text('{"query": {}}')
    (tmp_path / "queries" / "ms_defender.kql").write_text("DeviceEvents | where Timestamp > ago(7d)")
    (tmp_path / "queries" / "ms_defender_api.json").write_text('{"Query": "DeviceEvents | where Timestamp > ago(7d)"}')
    (tmp_path / "queries" / "elk_02.sql").write_text("SELECT 1")
    result = validate_playbook(tmp_path)
    assert result.success is True
    assert any("nonexistent" in w or "not found" in w for w in result.warnings)


# --- YAML format tests ---

YAML_VALID_METADATA = """
name: "YAML Playbook"
technique_description: "Test YAML format."
hunting_indicators: "Indicators."
true_positive_conditions: "TP."
false_positive_conditions: "FP."
data_sources:
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk.yml"
    query_id: q1
  - tool: "elk"
    mode: "API"
    query_path: "queries/elk.yml"
    query_ids: [q1, q2]
  - tool: "ms_defender"
    mode: "manual"
    query_path: "queries/ms_defender.yml"
    query_id: k1
  - tool: "ms_defender"
    mode: "API"
    query_path: "queries/ms_defender.yml"
    query_ids: [k1]
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk.yml"
    query_id: q2
"""


def test_validate_playbook_yaml_with_query_id(tmp_path):
    """YAML query_path with query_id passes validation."""
    (tmp_path / "metadata.yml").write_text(YAML_VALID_METADATA)
    (tmp_path / "queries").mkdir()
    (tmp_path / "queries" / "elk.yml").write_text("""
manual:
  q1:
    sql: "SELECT * FROM events WHERE timestamp >= NOW() - INTERVAL '7 days'"
  q2:
    sql: "SELECT 1 FROM events WHERE timestamp >= NOW() - INTERVAL '7 days'"
api:
  q1:
    body: { query: { range: { "@timestamp": { gte: "now-7d" } } } }
  q2:
    body: { query: { bool: { filter: [] } } }
""")
    (tmp_path / "queries" / "ms_defender.yml").write_text("""
manual:
  k1:
    kql: "DeviceEvents | where Timestamp > ago(7d)"
api:
  k1:
    body: { Query: "DeviceEvents | where Timestamp > ago(7d)" }
""")
    result = validate_playbook(tmp_path, validate_placeholders=False)
    assert result.success is True
    assert result.errors == []


def test_validate_playbook_yaml_missing_query_id(tmp_path):
    """YAML query_path without query_id or query_ids fails."""
    (tmp_path / "metadata.yml").write_text(YAML_VALID_METADATA.replace(
        'query_path: "queries/elk.yml"\n    query_id: q1',
        'query_path: "queries/elk.yml"'
    ))
    (tmp_path / "queries").mkdir()
    (tmp_path / "queries" / "elk.yml").write_text("manual:\n  q1:\n    sql: 'SELECT 1'\napi:\n  q1:\n    body: {}")
    (tmp_path / "queries" / "ms_defender.yml").write_text("manual:\n  k1:\n    kql: 'DeviceEvents'\napi:\n  k1:\n    body: {}")
    result = validate_playbook(tmp_path, validate_placeholders=False)
    assert result.success is False
    assert any("query_id" in e or "query_ids" in e for e in result.errors)


def test_validate_playbook_yaml_query_id_not_found(tmp_path):
    """YAML with query_id not present in file fails."""
    (tmp_path / "metadata.yml").write_text(YAML_VALID_METADATA.replace("query_id: q1", "query_id: nonexistent"))
    (tmp_path / "queries").mkdir()
    (tmp_path / "queries" / "elk.yml").write_text("""
manual:
  q1:
    sql: "SELECT 1"
api:
  q1:
    body: {}
""")
    (tmp_path / "queries" / "ms_defender.yml").write_text("manual:\n  k1:\n    kql: 'DeviceEvents'\napi:\n  k1:\n    body: {}")
    result = validate_playbook(tmp_path, validate_placeholders=False)
    assert result.success is False
    assert any("nonexistent" in e for e in result.errors)


def test_validate_playbook_yaml_relative_time(tmp_path):
    """YAML format: relative time in query content passes with no warnings."""
    (tmp_path / "metadata.yml").write_text(YAML_VALID_METADATA)
    (tmp_path / "queries").mkdir()
    (tmp_path / "queries" / "elk.yml").write_text("""
manual:
  q1:
    sql: "SELECT * FROM events WHERE timestamp >= NOW() - INTERVAL '7 days'"
  q2:
    sql: "SELECT 1"
api:
  q1:
    body: { query: { range: { "@timestamp": { gte: "now-7d", lte: "now" } } } }
  q2:
    body: { query: { bool: { filter: [] } } }
""")
    (tmp_path / "queries" / "ms_defender.yml").write_text("""
manual:
  k1:
    kql: "DeviceEvents | where Timestamp > ago(7d)"
api:
  k1:
    body: { Query: "DeviceEvents | where Timestamp > ago(7d)" }
""")
    result = validate_playbook(tmp_path)
    assert result.success is True
    assert not any("relative" in w or "absolute" in w for w in result.warnings)
