"""
Configuration validator – JSON Schema validation for config data.

Validates dict (e.g. from YAML) against JSON Schema. Rejects invalid data
and returns a list of error messages. Supports schema versioning via schema_path
or schema_version parameter.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import jsonschema
import yaml


def _load_schema(schema_path: Union[str, Path, dict]) -> dict:
    """Load schema from path (JSON/YAML) or return dict as-is."""
    if isinstance(schema_path, dict):
        return schema_path
    path = Path(schema_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Schema file not found: {path}")
    with open(path) as f:
        if path.suffix in (".yml", ".yaml"):
            return yaml.safe_load(f) or {}
        return json.load(f)


def validate_all_required_fields(config_data: dict, schema: dict) -> List[str]:
    """
    Return list of missing required field names from schema["required"].

    Does not perform full validation; only checks presence of required keys.
    """
    required = schema.get("required")
    if not required:
        return []
    missing = [k for k in required if k not in config_data]
    return missing


def validate_config(
    config_data: dict,
    schema_path: Union[str, Path, dict],
    schema_version: Optional[str] = None,
) -> Tuple[bool, List[str]]:
    """
    Validate config_data against JSON Schema.

    Args:
        config_data: Configuration dict (e.g. from YAML).
        schema_path: Path to JSON/YAML schema file or dict schema.
        schema_version: Optional version hint; if schema_dir has versioned files
            (e.g. central_config_v1.json), can be used to select one.

    Returns:
        (True, []) if valid; (False, list_of_error_messages) if invalid.

    Schema may use additionalProperties: false; validator rejects extra keys.
    """
    schema = _load_schema(schema_path)
    if schema_version is not None and isinstance(schema_path, (str, Path)):
        path = Path(schema_path)
        if path.is_file():
            parent = path.parent
            versioned = parent / f"{path.stem}_v{schema_version}.json"
            if versioned.is_file():
                schema = _load_schema(versioned)

    errors: List[str] = []
    try:
        jsonschema.validate(instance=config_data, schema=schema)
        return (True, [])
    except jsonschema.ValidationError as e:
        errors.append(str(e))
        for sub in (e.context or []):
            errors.append(str(sub))
        return (False, errors)
    except jsonschema.SchemaError as e:
        errors.append(f"Invalid schema: {e}")
        return (False, errors)
