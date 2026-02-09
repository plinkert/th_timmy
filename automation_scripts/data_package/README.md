# Data Package (Step 1.5)

Standard format for threat hunting pipeline data. Unifies structures from different sources (manual/API). Validates with JSON Schema.

## Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | yes | Unique package identifier |
| source | string | yes | Data source (elk, ms_defender, manual) |
| timestamp | string | yes | ISO 8601 (e.g. 2025-01-27T12:00:00Z) |
| data | array of objects | yes | Query results (max 100k items) |
| anonymized | boolean | yes | Whether data is anonymized |
| context | object | no | Optional (playbook_id, hunt_id, tool, mode) |

## Usage

```python
from automation_scripts.data_package import DataPackage, DataPackageValidationError

# Create
dp = DataPackage(
    id="pkg-001",
    source="elk",
    timestamp="2025-01-27T12:00:00Z",
    data=[{"event_id": "1", "host": "vm01"}],
    anonymized=True,
    context={"playbook_id": "T1059"},
)

# Validate (raises DataPackageValidationError on failure)
dp.validate()  # uses default schema path
dp.validate(schema_path=Path("configs/schemas/data_package_schema.json"))

# Require anonymized before AI
dp.validate(require_anonymized_for_ai=True)  # raises if anonymized=False

# Serialization
d = dp.to_dict()
s = dp.to_json()
dp2 = DataPackage.from_dict(d, validate_on_load=True)
dp3 = DataPackage.from_json(s, validate_on_load=True)
```

## Limits

- **Size**: 5 MB (MAX_DATA_PACKAGE_SIZE_BYTES). Configurable via `max_size_bytes` in `validate()`.
- **Items**: maxItems 100000 in schema.

## Schema

`configs/schemas/data_package_schema.json` (JSON Schema draft-07).

## Pipeline Location

DataPackage is created after query results are collected and anonymized; passed to Playbook Engine (Step 2.1) and AI (Step 3.1).
