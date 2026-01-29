"""
Playbook validator – validates metadata.yml (technique_description, data_sources).

Rejects playbooks without required fields. Uses JSON Schema for structure validation.
Logs validation results and errors.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

import jsonschema
import yaml

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of playbook validation."""

    success: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def _load_metadata(playbook_dir: Union[str, Path]) -> dict:
    """Load metadata.yml from playbook directory."""
    path = Path(playbook_dir).resolve() / "metadata.yml"
    if not path.is_file():
        raise FileNotFoundError(f"metadata.yml not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _load_schema(schema_path: Optional[Union[str, Path]]) -> dict:
    """Load JSON Schema from path. Returns default schema if path is None or invalid."""
    if schema_path is None:
        return _default_schema()
    path = Path(schema_path).resolve()
    if not path.is_file():
        logger.warning("Schema file not found %s, using default", path)
        return _default_schema()
    with open(path) as f:
        return json.load(f)


def _default_schema() -> dict:
    """Default JSON Schema for playbook metadata."""
    return {
        "type": "object",
        "required": ["technique_description", "data_sources"],
        "properties": {
            "technique_description": {"type": "string", "minLength": 1},
            "data_sources": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["tool", "mode", "query_path"],
                    "properties": {
                        "tool": {"type": "string", "minLength": 1},
                        "mode": {"enum": ["manual", "API"]},
                        "query_path": {"type": "string", "minLength": 1},
                    },
                },
            },
        },
    }


def validate_playbook(
    playbook_dir: Union[str, Path],
    schema_path: Optional[Union[str, Path]] = None,
) -> ValidationResult:
    """
    Validate playbook metadata.yml.

    Checks presence of technique_description and data_sources, validates structure
    against JSON Schema. Returns ValidationResult with success, errors, warnings.
    """
    errors: List[str] = []
    warnings: List[str] = []

    try:
        metadata = _load_metadata(playbook_dir)
    except FileNotFoundError as e:
        errors.append(str(e))
        logger.error("Playbook validation failed: %s", e)
        return ValidationResult(success=False, errors=errors, warnings=warnings)

    # technique_description – required, non-empty
    td = metadata.get("technique_description")
    if td is None:
        errors.append("technique_description is required (used as report intro)")
    elif not isinstance(td, str):
        errors.append("technique_description must be a string")
    elif not td.strip():
        errors.append("technique_description is required (used as report intro)")

    # data_sources – required, non-empty list
    ds = metadata.get("data_sources")
    if ds is None:
        errors.append("data_sources section is required")
    elif not isinstance(ds, list):
        errors.append("data_sources must be a list")
    elif len(ds) == 0:
        errors.append("data_sources must contain at least one entry")
    else:
        for i, entry in enumerate(ds):
            if not isinstance(entry, dict):
                errors.append(f"data_sources[{i}]: entry must be an object")
                continue
            for field_name in ("tool", "mode", "query_path"):
                if field_name not in entry:
                    errors.append(f"data_sources[{i}]: missing required field '{field_name}'")
            mode = entry.get("mode")
            if mode is not None and mode not in ("manual", "API"):
                errors.append(f"data_sources[{i}]: mode must be 'manual' or 'API', got {mode!r}")

    if errors:
        for e in errors:
            logger.error("Playbook validation error: %s", e)
        return ValidationResult(success=False, errors=errors, warnings=warnings)

    # JSON Schema validation
    schema = _load_schema(schema_path)
    try:
        jsonschema.validate(instance=metadata, schema=schema)
    except jsonschema.ValidationError as e:
        errors.append(str(e))
        logger.error("Playbook schema validation failed: %s", e)
        return ValidationResult(success=False, errors=errors, warnings=warnings)
    except jsonschema.SchemaError as e:
        errors.append(f"Schema error: {e}")
        logger.error("Schema error: %s", e)
        return ValidationResult(success=False, errors=errors, warnings=warnings)

    logger.info("Playbook validation passed: %s", playbook_dir)
    return ValidationResult(success=True, errors=[], warnings=warnings)
