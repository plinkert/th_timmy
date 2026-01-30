"""Unit tests for query_generator (Step 1.2)."""

from pathlib import Path

import pytest

from automation_scripts.playbooks.query_generator import (
    QueryGeneratorError,
    generate_queries,
    resolve_playbook_dir,
)


def test_generate_queries_returns_paths(tmp_path):
    """generate_queries returns non-empty list of Path for valid input."""
    playbooks_dir = tmp_path / "playbooks"
    playbooks_dir.mkdir()
    pb = playbooks_dir / "T1059-command-scripting-interpreter"
    pb.mkdir()
    (pb / "metadata.yml").write_text("""
technique_description: "Test"
hunting_indicators: "Indicators"
true_positive_conditions: "TP"
false_positive_conditions: "FP"
mitre_technique_id: "T1059"
data_sources:
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk.yml"
    query_id: q1
  - tool: "elk"
    mode: "API"
    query_path: "queries/elk.yml"
    query_id: q1
  - tool: "ms_defender"
    mode: "manual"
    query_path: "queries/ms_defender.yml"
    query_id: k1
  - tool: "ms_defender"
    mode: "API"
    query_path: "queries/ms_defender.yml"
    query_id: k1
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk.yml"
    query_id: q2
""")
    (pb / "queries").mkdir()
    (pb / "queries" / "elk.yml").write_text("""
manual:
  q1:
    sql: "SELECT 1"
  q2:
    sql: "SELECT 2"
api:
  q1:
    body: { query: {} }
""")
    (pb / "queries" / "ms_defender.yml").write_text("""
manual:
  k1:
    kql: "DeviceEvents | take 10"
api:
  k1:
    body: { Query: "DeviceEvents" }
""")

    out_dir = tmp_path / "queries_generated"
    paths = generate_queries(
        hunt_list=["T1059"],
        tool_list=["elk", "ms_defender"],
        mode="manual",
        output_dir=out_dir,
        playbooks_dir=playbooks_dir,
        project_root=tmp_path,
    )
    assert len(paths) >= 1
    for p in paths:
        assert p.exists()
        assert "{{" not in p.read_text(), f"Generated file should not contain placeholders: {p}"


def test_generate_queries_files_exist_and_no_placeholders(tmp_path):
    """Generated files exist and do not contain {{ placeholders."""
    playbooks_dir = tmp_path / "playbooks"
    playbooks_dir.mkdir()
    pb = playbooks_dir / "T1055-process-injection"
    pb.mkdir()
    (pb / "metadata.yml").write_text("""
technique_description: "Test"
hunting_indicators: "Indicators"
true_positive_conditions: "TP"
false_positive_conditions: "FP"
mitre_technique_id: "T1055"
data_sources:
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk.yml"
    query_id: q1
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk.yml"
    query_id: q2
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk.yml"
    query_id: q3
  - tool: "ms_defender"
    mode: "manual"
    query_path: "queries/ms_defender.yml"
    query_id: k1
  - tool: "ms_defender"
    mode: "manual"
    query_path: "queries/ms_defender.yml"
    query_id: k2
""")
    (pb / "queries").mkdir()
    (pb / "queries" / "elk.yml").write_text("""
manual:
  q1:
    sql: "SELECT * WHERE ts >= {{timestamp_start}}"
  q2:
    sql: "SELECT 2"
  q3:
    sql: "SELECT 3"
api: {}
""")
    (pb / "queries" / "ms_defender.yml").write_text("""
manual:
  k1:
    kql: "DeviceEvents | where Timestamp > ago(7d)"
  k2:
    kql: "DeviceEvents | take 5"
api: {}
""")

    out_dir = tmp_path / "out"
    paths = generate_queries(
        hunt_list=["T1055"],
        tool_list=["elk", "ms_defender"],
        mode="manual",
        output_dir=out_dir,
        time_range_days=7,
        playbooks_dir=playbooks_dir,
        project_root=tmp_path,
    )
    for p in paths:
        content = p.read_text()
        assert "{{timestamp_start}}" not in content
        assert "{{timestamp_end}}" not in content


def test_generate_queries_empty_hunt_list():
    """Empty hunt_list raises QueryGeneratorError."""
    with pytest.raises(QueryGeneratorError) as exc_info:
        generate_queries(
            hunt_list=[],
            tool_list=["elk"],
            mode="manual",
            project_root="/tmp",
        )
    assert "hunt_list" in str(exc_info.value).lower() or "empty" in str(exc_info.value).lower()


def test_generate_queries_unsupported_tool():
    """Unsupported tool raises QueryGeneratorError."""
    with pytest.raises(QueryGeneratorError) as exc_info:
        generate_queries(
            hunt_list=["T1059"],
            tool_list=["splunk"],
            mode="manual",
            project_root="/tmp",
        )
    assert "splunk" in str(exc_info.value).lower() or "unsupported" in str(exc_info.value).lower()


def test_resolve_playbook_dir_by_full_id(tmp_path):
    """resolve_playbook_dir finds playbook by full ID."""
    playbooks_dir = tmp_path / "playbooks"
    playbooks_dir.mkdir()
    pb = playbooks_dir / "T1059-command-scripting-interpreter"
    pb.mkdir()
    result = resolve_playbook_dir("T1059-command-scripting-interpreter", playbooks_dir)
    assert result == pb


def test_resolve_playbook_dir_by_short_id(tmp_path):
    """resolve_playbook_dir finds playbook by short ID (T1059)."""
    playbooks_dir = tmp_path / "playbooks"
    playbooks_dir.mkdir()
    pb = playbooks_dir / "T1059-command-scripting-interpreter"
    pb.mkdir()
    result = resolve_playbook_dir("T1059", playbooks_dir)
    assert result == pb


def test_resolve_playbook_dir_not_found(tmp_path):
    """resolve_playbook_dir raises QueryGeneratorError when not found."""
    playbooks_dir = tmp_path / "playbooks"
    playbooks_dir.mkdir()
    with pytest.raises(QueryGeneratorError) as exc_info:
        resolve_playbook_dir("T9999", playbooks_dir)
    assert "T9999" in str(exc_info.value) or "not found" in str(exc_info.value).lower()
