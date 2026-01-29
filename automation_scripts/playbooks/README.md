# Playbook Structure (Step 1.1)

Playbook validator and query loader for threat hunting playbooks with `data_sources` section.

## Overview

- **playbook_validator** – validates `metadata.yml` (technique_description, data_sources, JSON Schema)
- **query_loader** – loads query files (.sql, .json, .kql) from playbook `queries/` directory

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
        print(f"{e.tool} {e.mode}: {e.query_path}")
except QueryLoadError as e:
    print(e)
```

## Configuration

- **Schema:** `configs/schemas/playbook_metadata.json` (optional; default schema used if not found)
- **Playbooks:** `playbooks/` directory (template + 5 MITRE ATT&CK playbooks)

## Tests

```bash
./hosts/vm04-orchestrator/run_python.sh -m pytest tests/unit/test_playbook_validator.py tests/unit/test_query_loader.py -v
./tests/integration/run_playbooks_integration.sh
```

## Documentation

See [docs/PLAYBOOKS.md](../../../docs/PLAYBOOKS.md) for format, examples, and API details.
