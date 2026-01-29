# Playbook Structure (Step 1.1)

Playbook validator and query loader for threat hunting playbooks with `data_sources` section.

## Overview

- **playbook_validator** – validates `metadata.yml` (technique_description, data_sources, hunting_indicators, TP/FP, tool_class enum) and optionally checks relative time in query files; for YAML query_path requires `query_id` or `query_ids` and validates query existence
- **query_loader** – loads query files (.sql, .json, .kql or .yml/.yaml) from playbook `queries/` directory; supports `tool_class` (siem, edr, data_lake); for YAML uses `query_id`/`query_ids` to load specific queries from manual/api sections. **Backward compatible:** legacy format (.sql, .kql, .json per file) still works when `query_path` points to a single-file query.

## Requirements

- Python 3.10+
- PyYAML, jsonschema (from project requirements.txt)

## Usage

```python
from automation_scripts.playbooks import validate_playbook, load_queries, QueryLoadError

# Validate playbook
result = validate_playbook("/path/to/playbook")
if not result.success:
    for err in result.errors:
        print(err)

# Load queries
try:
    entries = load_queries("/path/to/playbook")
    for e in entries:
        print(f"{e.tool} {e.mode}: {e.query_path}" + (f" query_id={e.query_id}" if getattr(e, 'query_id', None) else ""))
except QueryLoadError as e:
    print(e)
```

## QueryEntry

`load_queries()` returns `QueryEntry` objects. Fields: `tool`, `mode`, `query_path`, `content`, `tool_class`. For YAML queries, `query_id` is set (optional; identifies the query block within the YAML file).

## Configuration

- **Schema:** `configs/schemas/playbook_metadata.json` (optional; default schema used if not found)
- **Playbooks:** `playbooks/` directory (template + 5 MITRE ATT&CK playbooks)

## CLI and Jupyter

```bash
# CLI – browse playbooks (dry run)
python scripts/th_playbook.py list
python scripts/th_playbook.py show T1055-process-injection
python scripts/th_playbook.py queries T1055-process-injection --resolve --hours 24
python scripts/th_playbook.py validate
```

Jupyter: use `notebooks/playbook_browser.ipynb` or import `list_playbooks`, `show_playbook`, `get_queries_resolved` from `automation_scripts.playbooks`.

## Tests

```bash
./hosts/vm04-orchestrator/run_python.sh -m pytest tests/unit/test_playbook_validator.py tests/unit/test_query_loader.py tests/unit/test_cli_helpers.py -v
./tests/integration/run_playbooks_integration.sh
```

## Documentation

See [docs/PLAYBOOKS.md](../../../docs/PLAYBOOKS.md) for format, examples, and API details.
