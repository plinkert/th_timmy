# Playbook Structure and data_sources (Step 1.1)

This document describes the playbook structure with `data_sources` section, query format, and how to use the validator and query loader.

## Overview

Each playbook is a directory containing:
- `metadata.yml` – playbook metadata with `technique_description` and `data_sources`
- `queries/` – query files (`.sql`, `.json`, `.kql` or `.yml`/`.yaml`) referenced by `data_sources`

Playbooks are versioned in the repository and synchronized to VMs via Step 0.2 (Repository Sync).

## metadata.yml Format

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| **technique_description** | string | Description of the MITRE ATT&CK technique. Used as **intro to the technical section** in the hunt report. Must be non-empty. |
| **hunting_indicators** | string | What is being searched for – key indicators, event types, process names, command patterns. Must be non-empty. |
| **true_positive_conditions** | string | When to treat a finding as True Positive (confirmed malicious activity). Must be non-empty. |
| **false_positive_conditions** | string | When to treat a finding as False Positive (benign/legitimate activity). Must be non-empty. |
| **data_sources** | array | List of data source entries. Must contain **at least 5 queries** per technique. |

### data_sources Entry Format

Each entry in `data_sources` must have:

| Field | Type | Description |
|-------|------|-------------|
| **tool_class** | string | Optional. Tool class: `siem`, `edr`, `data_lake`. Analyst selects class to get queries for available tool. |
| **tool** | string | Tool implementation (e.g. `elk`, `ms_defender`, `splunk`). |
| **mode** | string | Execution mode: `manual` or `API`. |
| **query_path** | string | Relative path to the query file (e.g. `queries/elk_manual.sql` or `queries/elk.yml`). Path is relative to the playbook directory. |
| **query_id** | string | *Required for YAML.* Id of query in YAML file (manual/api section). Use when `query_path` is `.yml`/`.yaml`. |
| **query_ids** | array | *Required for YAML.* List of query ids – loader expands to multiple `QueryEntry`. Alternative to `query_id`. |
| **required_indices** | array | Optional. SIEM index patterns (e.g. `["sysmon-*", "winlogbeat-*"]`). Used for Elasticsearch/ELK. |

**Tool classes** (universal – analyst picks available tool):
- **siem** – SIEM (ELK, Splunk, MS Sentinel)
- **edr** – EDR (Microsoft Defender, CrowdStrike)
- **data_lake** – Data Lake / analytics

**Tool class mapping** (tool_class → tool implementations):
| tool_class | tool implementations |
|------------|----------------------|
| siem | elk, splunk, ms_sentinel |
| edr | ms_defender |
| data_lake | elk (optional, large-scale analytics) |

### Example

```yaml
name: "Process Injection"
description: "Detect code injection into processes"
version: "1.0"
mitre_technique_id: "T1055"
mitre_technique_name: "Process Injection"

technique_description: |
  Process Injection is a technique where adversaries inject malicious code
  into the address space of another process. Common APIs include VirtualAllocEx,
  WriteProcessMemory, CreateRemoteThread.

data_sources:
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk_manual.sql"
  - tool: "elk"
    mode: "API"
    query_path: "queries/elk_api.json"
  - tool: "ms_defender"
    mode: "manual"
    query_path: "queries/ms_defender_manual.kql"
  - tool: "ms_defender"
    mode: "API"
    query_path: "queries/ms_defender_api.json"
```

## Query File Formats

### Supported Extensions

| Extension | Tool | Description |
|-----------|------|-------------|
| `.sql` | elk, splunk | SQL query for manual execution. |
| `.json` | elk, ms_defender | JSON body for API (Elasticsearch DSL, Microsoft Defender API). |
| `.kql` | ms_defender | Kusto Query Language for Microsoft Defender Advanced Hunting. |
| `.yml` / `.yaml` | elk, ms_defender | YAML file with multiple queries. Requires `query_id` or `query_ids` in `data_sources`. |

### YAML Format (elk.yml, ms_defender.yml)

For `.yml`/`.yaml` query files, one file per tool groups multiple queries. The `metadata.yml` references them via `query_id` (single) or `query_ids` (list):

```yaml
data_sources:
  - tool: "elk"
    mode: "manual"
    query_path: "queries/elk.yml"
    query_ids: [memory_ops, sysmon_event_10, sysmon_event_8]
  - tool: "elk"
    mode: "API"
    query_path: "queries/elk.yml"
    query_id: memory_ops
```

YAML structure: `manual` and `api` sections, each with named query blocks:

```yaml
# elk.yml
manual:
  memory_ops:
    sql: |
      SELECT * FROM sysmon_events
      WHERE timestamp >= NOW() - INTERVAL '7 days'
  sysmon_event_10:
    sql: "SELECT * FROM sysmon_events WHERE event_code = 10 ..."
api:
  memory_ops:
    body:
      query:
        bool:
          filter:
            - range: { "@timestamp": { "gte": "now-7d", "lte": "now" } }
```

For `ms_defender.yml`: use `kql` in `manual` and `body` (with `Query` key) in `api`.

### Query Time Format – Relative Time Only

Queries **must use relative time** (e.g. last 7 days, last 30 days), not absolute timestamps.

| Tool | Format | Example |
|------|--------|---------|
| **SQL** | `NOW() - INTERVAL '7 days'` | `timestamp >= NOW() - INTERVAL '7 days'` |
| **KQL (Microsoft Defender)** | `ago(7d)` | `Timestamp > ago(7d)` |
| **Elasticsearch** | `now-7d`, `now` | `"gte": "now-7d", "lte": "now"` |

For last 30 days: use `INTERVAL '30 days'`, `ago(30d)`, `now-30d`.

### Example: elk_manual.sql

```sql
-- Relative time: last 7 days (change INTERVAL for 30 days: INTERVAL '30 days')
SELECT *
FROM events
WHERE process_name LIKE '%powershell%'
  AND timestamp >= NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC;
```

### Example: elk_api.json

```json
{
  "query": {
    "bool": {
      "filter": [
        { "range": { "@timestamp": { "gte": "now-7d", "lte": "now" } } },
        { "match": { "process.name": "powershell" } }
      ]
    }
  }
}
```

### Example: ms_defender_manual.kql

```kql
// Microsoft Defender Advanced Hunting - relative time: last 7 days
DeviceProcessEvents
| where Timestamp > ago(7d)
| where FileName =~ "powershell.exe"
| project Timestamp, DeviceName, FileName, ProcessCommandLine
```

## Python API

### playbook_validator

```python
from automation_scripts.playbooks import validate_playbook, ValidationResult

result = validate_playbook("/path/to/playbook")
if result.success:
    print("Playbook valid")
else:
    for err in result.errors:
        print(f"Error: {err}")
```

### query_loader

```python
from automation_scripts.playbooks import load_queries, QueryEntry, QueryLoadError

try:
    entries = load_queries("/path/to/playbook")
    for e in entries:
        print(f"{e.tool} {e.mode}: {e.query_path} ({len(e.content)} chars)")
except QueryLoadError as e:
    print(f"Load failed: {e}")
```

### Recommended Fields (hypothesis, environment_requirements, operational_steps, escalation)

| Field | Description |
|-------|-------------|
| **environment_requirements** | Tool classes (EDR, SIEM, Data Lake), min retention, permissions |
| **hypothesis** | trigger, statement, goal, scope – hunt hypothesis |
| **operational_steps** | Step-by-step hunt workflow (input, operation, success_criteria, outcome) |
| **escalation** | on_confirmed, notification_roles, ir_playbook_ref |

These fields are recommended; missing fields generate warnings during validation.

## CLI and Jupyter Browsing

### CLI (scripts/th_playbook.py)

Browse playbooks from terminal or Jupyter (dry run – no ELK/MS Defender connection):

```bash
# List playbooks (optionally show tool_classes)
python scripts/th_playbook.py list
python scripts/th_playbook.py list --tool-classes

# Show playbook metadata (hypothesis, operational_steps, escalation)
python scripts/th_playbook.py show T1055-process-injection

# Show queries (filter by tool_class: siem, edr, data_lake)
python scripts/th_playbook.py queries T1055-process-injection --tool-class edr
python scripts/th_playbook.py queries T1055-process-injection --tool-class siem
python scripts/th_playbook.py queries T1055-process-injection --resolve --hours 24

# Validate playbook(s)
python scripts/th_playbook.py validate
python scripts/th_playbook.py validate T1055-process-injection
```

Set `PROJECT_ROOT` or `BOOTSTRAP_PROJECT_ROOT` if not running from project root.

### Jupyter Notebook

Use `notebooks/playbook_browser.ipynb` to browse playbooks interactively:

```python
from automation_scripts.playbooks import list_playbooks, show_playbook, get_queries_resolved

# List playbooks (includes tool_classes from environment_requirements)
list_playbooks()

# Show metadata (hypothesis, operational_steps, escalation)
show_playbook("T1055-process-injection")

# Get queries (filter by tool_class)
queries = get_queries_resolved("T1055-process-injection", hours=24, tool_class="edr")
queries = get_queries_resolved("T1055-process-injection", hours=24, tool_class="siem")
```

## Running Validator and Loader

### Unit Tests

```bash
./hosts/vm04-orchestrator/run_python.sh -m pytest tests/unit/test_playbook_validator.py tests/unit/test_query_loader.py -v
```

### Integration Test

```bash
./tests/integration/run_playbooks_integration.sh
```

## Required Metadata Fields (TP/FP)

Every playbook **must** include these fields for proper hunt interpretation:

| Field | Description |
|-------|-------------|
| **hunting_indicators** | What is being searched for – key indicators, event types, process names |
| **true_positive_conditions** | When to treat a finding as True Positive (confirmed malicious) |
| **false_positive_conditions** | When to treat a finding as False Positive (benign/legitimate) |

These fields help analysts interpret hunt results and reduce false positives.

## Playbook Sections: output, triage, response

### output

Defines expected query result format. Required columns for SIEM and EDR.

| Section | Fields |
|---------|--------|
| **siem** | `required_columns`, `description` – columns expected from SIEM queries (e.g. timestamp, event_code, process_name, target_process, command_line, parent_process) |
| **edr** | `required_columns`, `description` – columns expected from EDR queries (e.g. Timestamp, DeviceName, ActionType, FileName, ProcessCommandLine, InitiatingProcessFileName) |

### triage

Quick verification steps before full analysis. Reduces false positives.

| Field | Description |
|-------|-------------|
| **steps** | List of steps: `action`, `quick_reject`, `escalate` per step |
| **quick_fp_criteria** | Conditions for quick False Positive (e.g. parent is known AV/EDR/browser) |
| **quick_tp_criteria** | Conditions for quick True Positive (e.g. script host → lsass/csrss) |

### response

Actions when threat is confirmed.

| Field | Description |
|-------|-------------|
| **on_confirmed** | List of actions (isolate, collect artifacts, notify) |
| **ir_playbook_ref** | Reference to Incident Response playbook |
| **artifacts_to_collect** | List of artifacts to preserve (memory dump, process tree, registry) |
| **containment_notes** | Notes for containment decision |

### Example (shortened)

```yaml
output:
  siem:
    required_columns: [timestamp, event_code, process_name, target_process, command_line, parent_process]
  edr:
    required_columns: [Timestamp, DeviceName, ActionType, FileName, ProcessCommandLine, InitiatingProcessFileName]

triage:
  steps:
    - action: "Check InitiatingProcessFileName"
      quick_reject: "Known benign: svchost, SearchIndexer, browser child"
      escalate: "Unknown or script host (powershell, wscript)"
  quick_fp_criteria: ["Parent is known AV/EDR/browser"]
  quick_tp_criteria: ["Script host (powershell) -> lsass/csrss"]

response:
  on_confirmed: ["Open incident", "Isolate host", "Collect artifacts"]
  ir_playbook_ref: "IR-001-Malware-Response"
  artifacts_to_collect: ["Memory dump", "Process tree snapshot"]
  containment_notes: "Isolation decision per IR playbook"
```

## Example Playbooks

The repository includes 5 example playbooks based on MITRE ATT&CK (Picus Red Report 2024):

| Playbook | MITRE ID | Technique |
|----------|----------|-----------|
| T1055-process-injection | T1055 | Process Injection |
| T1059-command-scripting-interpreter | T1059 | Command and Scripting Interpreter |
| T1562-impair-defenses | T1562 | Impair Defenses |
| T1082-system-information-discovery | T1082 | System Information Discovery |
| T1486-data-encrypted-for-impact | T1486 | Data Encrypted for Impact (ransomware) |

Each playbook has `metadata.yml` with `technique_description` and `data_sources`, and `queries/` with elk and ms_defender query files. MITRE playbooks use YAML format (`elk.yml`, `ms_defender.yml`) with `query_id`/`query_ids`.
