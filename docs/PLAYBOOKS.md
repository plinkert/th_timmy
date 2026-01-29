# Playbook Structure and data_sources (Step 1.1)

This document describes the playbook structure with `data_sources` section, query format, and how to use the validator and query loader.

## Overview

Each playbook is a directory containing:
- `metadata.yml` – playbook metadata with `technique_description` and `data_sources`
- `queries/` – query files (`.sql`, `.json`, `.kql`) referenced by `data_sources`

Playbooks are versioned in the repository and synchronized to VMs via Step 0.2 (Repository Sync).

## metadata.yml Format

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| **technique_description** | string | Description of the MITRE ATT&CK technique. Used as **intro to the technical section** in the hunt report. Must be non-empty. |
| **data_sources** | array | List of data source entries. Must contain at least one entry. |

### data_sources Entry Format

Each entry in `data_sources` must have:

| Field | Type | Description |
|-------|------|-------------|
| **tool** | string | Tool identifier (e.g. `elk`, `ms_defender`, `splunk`). Any string. |
| **mode** | string | Execution mode: `manual` or `API`. |
| **query_path** | string | Relative path to the query file (e.g. `queries/elk_manual.sql`). Path is relative to the playbook directory. |

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

### Recommended Fields in Query Content

For consistency and future automation, queries should include:
- **timestamp** – time range (e.g. `{{timestamp_start}}`, `{{timestamp_end}}` placeholders)
- **id** – event or record identifier
- **Indicators** – fields relevant to the technique (process name, command line, etc.)

Placeholder substitution (e.g. `{{timestamp_start}}`) is documented here; implementation is in later steps.

### Example: elk_manual.sql

```sql
-- Required placeholders: {{timestamp_start}}, {{timestamp_end}}
SELECT *
FROM events
WHERE process_name LIKE '%powershell%'
  AND timestamp >= '{{timestamp_start}}'
  AND timestamp <= '{{timestamp_end}}'
ORDER BY timestamp DESC;
```

### Example: elk_api.json

```json
{
  "query": {
    "bool": {
      "filter": [
        { "range": { "@timestamp": { "gte": "{{timestamp_start}}", "lte": "{{timestamp_end}}" } } },
        { "match": { "process.name": "powershell" } }
      ]
    }
  }
}
```

### Example: ms_defender_manual.kql

```kql
// Microsoft Defender Advanced Hunting
DeviceProcessEvents
| where Timestamp between (datetime({{timestamp_start}}) .. datetime({{timestamp_end}}))
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

## Running Validator and Loader

### Unit Tests

```bash
./hosts/vm04-orchestrator/run_python.sh -m pytest tests/unit/test_playbook_validator.py tests/unit/test_query_loader.py -v
```

### Integration Test

```bash
./tests/integration/run_playbooks_integration.sh
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

Each playbook has `metadata.yml` with `technique_description` and `data_sources`, and `queries/` with elk and ms_defender query files.
