# Playbook Structure (Step 1.1), Query Generator (Step 1.2), Playbook Engine (Step 2.1)

Playbook validator, query loader, query generator, and deterministic analysis engine for threat hunting playbooks with `data_sources` section.

## Overview

- **playbook_validator** – validates `metadata.yml` (technique_description, data_sources, hunting_indicators, TP/FP, tool_class enum) and optionally checks relative time in query files; for YAML query_path requires `query_id` or `query_ids` and validates query existence
- **query_loader** – loads query files (.sql, .json, .kql or .yml/.yaml) from playbook `queries/` directory; supports `tool_class` (siem, edr, data_lake); for YAML uses `query_id`/`query_ids` to load specific queries from manual/api sections. **Backward compatible:** legacy format (.sql, .kql, .json per file) still works when `query_path` points to a single-file query.
- **query_generator** (Step 1.2) – generates ready-to-use query files from playbooks. Loads via query_loader, filters by tool and mode, optionally substitutes placeholders (`{{timestamp_start}}`, `{{timestamp_end}}`, `{{days}}`), saves to `queries_generated/`.
- **playbook_engine** (Step 2.1) – deterministic analysis: `run_analysis(data_package, playbook_metadata)` returns `List[Finding]`. Uses `analysis_rules` from metadata (e.g. type: threshold, event_type, threshold, window_minutes, group_by) and optional `field_mapping` for canonical field names. Findings reference evidence by indices in `DataPackage.data` (evidence_ids).

## Requirements

- Python 3.10+
- PyYAML, jsonschema (from project requirements.txt)

## Usage

```python
from automation_scripts.playbooks import validate_playbook, load_queries, QueryLoadError, run_analysis, Finding

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

# Playbook Engine (Step 2.1): run deterministic analysis on DataPackage
from automation_scripts.data_package import DataPackage

dp = DataPackage(id="pkg-1", source="elk", timestamp="2025-01-27T12:00:00Z", data=[...], anonymized=True)
meta = {"mitre_technique_id": "T1059", "analysis_rules": [{"type": "threshold", "threshold": 10, "group_by": "src_ip"}]}
findings = run_analysis(dp, meta)  # or run_analysis(dp, Path("playbooks/T1059-..."))
for f in findings:
    print(f.finding_id, f.description, f.evidence_ids)
```

## Finding (Step 2.1)

`run_analysis()` returns a list of `Finding` objects. Fields: `finding_id`, `description`, `severity`, `evidence_ids` (indices into `DataPackage.data`), `timestamp`, `playbook_id`, `context`. Use `finding.to_dict()` for serialization.

## analysis_rules and field_mapping

In `metadata.yml` (or playbook metadata dict) you can add:

- **analysis_rules**: list of rules. Supported type: `threshold`. Keys: `event_type` (optional filter), `threshold` (min count), `window_minutes` (optional time window), `group_by` (canonical field, default `src_ip`), `description`, `severity` (low/medium/high).
- **field_mapping**: optional map from canonical field names to lists of source keys (e.g. `src_ip: [source.ip, client_ip]`). Default mapping supports ELK (`@timestamp`, `source.ip`) and MS Defender (`TimeGenerated`, `SrcIp`) style keys.

## QueryEntry

`load_queries()` returns `QueryEntry` objects. Fields: `tool`, `mode`, `query_path`, `content`, `tool_class`. For YAML queries, `query_id` is set (optional; identifies the query block within the YAML file).

## Configuration

- **Schema:** `configs/schemas/playbook_metadata.json` (optional; default schema used if not found)
- **Playbooks:** `playbooks/` directory (template + 5 MITRE ATT&CK playbooks)

## Query Generator (Step 1.2)

```python
from automation_scripts.playbooks import generate_queries

# Generate queries for hunts T1059, T1055, T1562, tools elk+ms_defender, mode manual
paths = generate_queries(
    hunt_list=["T1059", "T1055", "T1562"],
    tool_list=["elk", "ms_defender"],
    mode="manual",
    output_dir="queries_generated",  # default: PROJECT_ROOT/queries_generated
    time_range_days=7,
)
# Returns list of Path; files saved as {hunt}_{tool}_{mode}_{query_id}.{sql|kql|json}
```

**Adding new templates:** Edit `query_templates.py` – add tool to `SUPPORTED_TOOLS`, add format to `TIMESTAMP_FORMATS` for manual/API. Placeholders: `{{timestamp_start}}`, `{{timestamp_end}}`, `{{days}}`.

## CLI and Jupyter

```bash
# CLI – browse playbooks (dry run)
python scripts/th_playbook.py list
python scripts/th_playbook.py show T1055-process-injection
python scripts/th_playbook.py queries T1055-process-injection --resolve --hours 24
python scripts/th_playbook.py validate

# Generate query files (Step 1.2)
python scripts/th_playbook.py generate T1059 T1055 T1562 -t elk ms_defender -m manual
python scripts/th_playbook.py generate T1055 -t ms_defender -m API -d 14 -o queries_generated
```

Jupyter: use `notebooks/playbook_browser.ipynb` or import `list_playbooks`, `show_playbook`, `get_queries_resolved`, `generate_queries` from `automation_scripts.playbooks`.

## Tests

```bash
./hosts/vm04-orchestrator/run_python.sh -m pytest tests/unit/test_playbook_validator.py tests/unit/test_query_loader.py tests/unit/test_cli_helpers.py tests/unit/test_query_templates.py tests/unit/test_query_generator.py tests/unit/test_playbook_engine.py -v
./tests/integration/run_playbooks_integration.sh
./tests/integration/run_query_generator_integration.sh
./tests/integration/run_playbook_engine_integration.sh
```

## Documentation

See [docs/PLAYBOOKS.md](../../../docs/PLAYBOOKS.md) for format, examples, and API details.
