"""Unit tests for playbook CLI helpers."""

from pathlib import Path

import pytest

from automation_scripts.playbooks.cli_helpers import (
    list_playbooks,
    show_playbook,
    get_queries_resolved,
    validate_playbook_cli,
    get_playbooks_dir,
)


def test_list_playbooks(tmp_path):
    """list_playbooks returns playbook summaries."""
    (tmp_path / "pb1").mkdir()
    (tmp_path / "pb1" / "metadata.yml").write_text("""
name: "Test 1"
mitre_technique_id: "T1234"
mitre_technique_name: "Test Technique"
description: "Short desc"
""")
    (tmp_path / "pb2").mkdir()
    (tmp_path / "pb2" / "metadata.yml").write_text("""
name: "Test 2"
""")
    items = list_playbooks(playbooks_dir=tmp_path)
    assert len(items) == 2
    ids = [i["id"] for i in items]
    assert "pb1" in ids
    assert "pb2" in ids
    pb1 = next(i for i in items if i["id"] == "pb1")
    assert pb1["name"] == "Test 1"
    assert pb1["mitre_technique_id"] == "T1234"


def test_list_playbooks_excludes_template(tmp_path):
    """list_playbooks excludes template by default."""
    (tmp_path / "template").mkdir()
    (tmp_path / "template" / "metadata.yml").write_text("name: Template")
    items = list_playbooks(playbooks_dir=tmp_path, include_template=False)
    assert not any(i["id"] == "template" for i in items)


def test_list_playbooks_includes_template(tmp_path):
    """list_playbooks includes template when requested."""
    (tmp_path / "template").mkdir()
    (tmp_path / "template" / "metadata.yml").write_text("name: Template")
    items = list_playbooks(playbooks_dir=tmp_path, include_template=True)
    assert any(i["id"] == "template" for i in items)


def test_show_playbook(tmp_path):
    """show_playbook returns metadata."""
    (tmp_path / "pb1").mkdir()
    (tmp_path / "pb1" / "metadata.yml").write_text("""
name: "Test"
mitre_technique_id: "T1234"
technique_description: "Long description here"
""")
    meta = show_playbook("pb1", playbooks_dir=tmp_path)
    assert meta["name"] == "Test"
    assert meta["mitre_technique_id"] == "T1234"
    assert "Long description" in meta["technique_description"]


def test_show_playbook_not_found(tmp_path):
    """show_playbook raises FileNotFoundError for missing playbook."""
    with pytest.raises(FileNotFoundError, match="not found"):
        show_playbook("nonexistent", playbooks_dir=tmp_path)


def test_get_queries_resolved(tmp_path):
    """get_queries_resolved substitutes placeholders."""
    (tmp_path / "pb1").mkdir()
    (tmp_path / "pb1" / "metadata.yml").write_text("""
technique_description: "Test"
data_sources:
  - tool: elk
    mode: manual
    query_path: queries/q.sql
""")
    (tmp_path / "pb1" / "queries").mkdir()
    (tmp_path / "pb1" / "queries" / "q.sql").write_text(
        "SELECT * FROM t WHERE ts >= '{{timestamp_start}}' AND ts <= '{{timestamp_end}}'"
    )
    entries = get_queries_resolved("pb1", hours=24, playbooks_dir=tmp_path)
    assert len(entries) == 1
    assert "{{timestamp_start}}" not in entries[0].content
    assert "{{timestamp_end}}" not in entries[0].content
    assert "T" in entries[0].content  # ISO timestamp format


def test_get_queries_resolved_not_found(tmp_path):
    """get_queries_resolved raises FileNotFoundError for missing playbook."""
    with pytest.raises(FileNotFoundError, match="not found"):
        get_queries_resolved("nonexistent", playbooks_dir=tmp_path)


def test_list_playbooks_includes_tool_classes(tmp_path):
    """list_playbooks returns tool_classes from environment_requirements."""
    (tmp_path / "pb1").mkdir()
    (tmp_path / "pb1" / "metadata.yml").write_text("""
name: "Test"
environment_requirements:
  tool_classes: [EDR, SIEM]
""")
    items = list_playbooks(playbooks_dir=tmp_path)
    assert len(items) == 1
    assert items[0].get("tool_classes") == ["EDR", "SIEM"]


def test_get_queries_resolved_filters_by_tool_class(tmp_path):
    """get_queries_resolved filters by tool_class when specified."""
    (tmp_path / "pb1").mkdir()
    (tmp_path / "pb1" / "metadata.yml").write_text("""
technique_description: "Test"
data_sources:
  - tool_class: "siem"
    tool: elk
    mode: manual
    query_path: queries/siem.sql
  - tool_class: "edr"
    tool: ms_defender
    mode: manual
    query_path: queries/edr.kql
""")
    (tmp_path / "pb1" / "queries").mkdir()
    (tmp_path / "pb1" / "queries" / "siem.sql").write_text("SELECT 1")
    (tmp_path / "pb1" / "queries" / "edr.kql").write_text("DeviceEvents")
    all_entries = get_queries_resolved("pb1", playbooks_dir=tmp_path)
    edr_entries = get_queries_resolved("pb1", playbooks_dir=tmp_path, tool_class="edr")
    siem_entries = get_queries_resolved("pb1", playbooks_dir=tmp_path, tool_class="siem")
    assert len(all_entries) == 2
    assert len(edr_entries) == 1
    assert edr_entries[0].tool_class == "edr"
    assert len(siem_entries) == 1
    assert siem_entries[0].tool_class == "siem"


def test_validate_playbook_cli_single(tmp_path):
    """validate_playbook_cli validates single playbook."""
    (tmp_path / "pb1").mkdir()
    (tmp_path / "pb1" / "metadata.yml").write_text("""
technique_description: "Test"
hunting_indicators: "Indicators"
true_positive_conditions: "TP"
false_positive_conditions: "FP"
data_sources:
  - tool: elk
    mode: manual
    query_path: queries/q1.sql
  - tool: elk
    mode: API
    query_path: queries/q2.json
  - tool: ms_defender
    mode: manual
    query_path: queries/q3.kql
  - tool: ms_defender
    mode: API
    query_path: queries/q4.json
  - tool: elk
    mode: manual
    query_path: queries/q5.sql
""")
    (tmp_path / "pb1" / "queries").mkdir()
    for f in ["q1.sql", "q2.json", "q3.kql", "q4.json", "q5.sql"]:
        (tmp_path / "pb1" / "queries" / f).write_text(
            "SELECT 1" if f.endswith(".sql") else "{}" if f.endswith(".json") else "DeviceEvents"
        )
    results = validate_playbook_cli(playbook_id="pb1", playbooks_dir=tmp_path)
    assert len(results) == 1
    assert results[0][0] == "pb1"
    assert results[0][1].success is True


def test_validate_playbook_cli_all(tmp_path):
    """validate_playbook_cli validates all playbooks when id omitted."""
    (tmp_path / "pb1").mkdir()
    (tmp_path / "pb1" / "metadata.yml").write_text("""
technique_description: "Test"
hunting_indicators: "Indicators"
true_positive_conditions: "TP"
false_positive_conditions: "FP"
data_sources:
  - tool: elk
    mode: manual
    query_path: queries/q1.sql
  - tool: elk
    mode: API
    query_path: queries/q2.json
  - tool: ms_defender
    mode: manual
    query_path: queries/q3.kql
  - tool: ms_defender
    mode: API
    query_path: queries/q4.json
  - tool: elk
    mode: manual
    query_path: queries/q5.sql
""")
    (tmp_path / "pb1" / "queries").mkdir()
    for f in ["q1.sql", "q2.json", "q3.kql", "q4.json", "q5.sql"]:
        (tmp_path / "pb1" / "queries" / f).write_text(
            "SELECT 1" if f.endswith(".sql") else "{}" if f.endswith(".json") else "DeviceEvents"
        )
    results = validate_playbook_cli(playbook_id=None, playbooks_dir=tmp_path)
    assert len(results) >= 1
    assert any(r[0] == "pb1" for r in results)
