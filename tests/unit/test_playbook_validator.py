"""Unit tests for playbook_validator (Step 1.1)."""

from pathlib import Path

import pytest

from automation_scripts.playbooks.playbook_validator import (
    validate_playbook,
    ValidationResult,
)


def test_validate_playbook_valid(tmp_path):
    """Valid playbook with technique_description and data_sources passes."""
    (tmp_path / "metadata.yml").write_text("""
name: "Test Playbook"
technique_description: "Test technique description for report intro."
data_sources:
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk.sql"
  - tool: "ms_defender"
    mode: "API"
    query_path: "queries/ms_defender.json"
""")
    result = validate_playbook(tmp_path)
    assert result.success is True
    assert result.errors == []


def test_validate_playbook_missing_technique_description(tmp_path):
    """Playbook without technique_description fails."""
    (tmp_path / "metadata.yml").write_text("""
name: "Test"
data_sources:
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk.sql"
""")
    result = validate_playbook(tmp_path)
    assert result.success is False
    assert any("technique_description" in e for e in result.errors)


def test_validate_playbook_empty_technique_description(tmp_path):
    """Playbook with empty technique_description fails."""
    (tmp_path / "metadata.yml").write_text("""
name: "Test"
technique_description: ""
data_sources:
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk.sql"
""")
    result = validate_playbook(tmp_path)
    assert result.success is False
    assert any("technique_description" in e for e in result.errors)


def test_validate_playbook_missing_data_sources(tmp_path):
    """Playbook without data_sources fails."""
    (tmp_path / "metadata.yml").write_text("""
name: "Test"
technique_description: "Valid description."
""")
    result = validate_playbook(tmp_path)
    assert result.success is False
    assert any("data_sources" in e for e in result.errors)


def test_validate_playbook_empty_data_sources(tmp_path):
    """Playbook with empty data_sources list fails."""
    (tmp_path / "metadata.yml").write_text("""
name: "Test"
technique_description: "Valid description."
data_sources: []
""")
    result = validate_playbook(tmp_path)
    assert result.success is False
    assert any("at least one" in e for e in result.errors)


def test_validate_playbook_invalid_mode(tmp_path):
    """Playbook with invalid mode (not manual/API) fails."""
    (tmp_path / "metadata.yml").write_text("""
name: "Test"
technique_description: "Valid description."
data_sources:
  - tool: "elk"
    mode: "automatic"
    query_path: "queries/elk.sql"
""")
    result = validate_playbook(tmp_path)
    assert result.success is False
    assert any("manual" in e or "API" in e for e in result.errors)


def test_validate_playbook_missing_tool(tmp_path):
    """Playbook with missing tool in data_sources entry fails."""
    (tmp_path / "metadata.yml").write_text("""
name: "Test"
technique_description: "Valid description."
data_sources:
  - mode: "manual"
    query_path: "queries/elk.sql"
""")
    result = validate_playbook(tmp_path)
    assert result.success is False
    assert any("tool" in e for e in result.errors)


def test_validate_playbook_missing_query_path(tmp_path):
    """Playbook with missing query_path in data_sources entry fails."""
    (tmp_path / "metadata.yml").write_text("""
name: "Test"
technique_description: "Valid description."
data_sources:
  - tool: "elk"
    mode: "manual"
""")
    result = validate_playbook(tmp_path)
    assert result.success is False
    assert any("query_path" in e for e in result.errors)


def test_validate_playbook_nonexistent_dir():
    """Playbook with nonexistent directory fails."""
    result = validate_playbook("/nonexistent/playbook/dir")
    assert result.success is False
    assert len(result.errors) >= 1


def test_validate_playbook_with_schema(tmp_path):
    """Valid playbook passes with custom schema path."""
    (tmp_path / "metadata.yml").write_text("""
technique_description: "Valid."
data_sources:
  - tool: "elk"
    mode: "API"
    query_path: "queries/elk.json"
""")
    schema_dir = Path(__file__).resolve().parent.parent.parent / "configs" / "schemas"
    schema_path = schema_dir / "playbook_metadata.json"
    if schema_path.exists():
        result = validate_playbook(tmp_path, schema_path=schema_path)
        assert result.success is True
