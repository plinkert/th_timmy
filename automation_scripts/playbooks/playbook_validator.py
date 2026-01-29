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
        "required": [
            "technique_description",
            "data_sources",
            "hunting_indicators",
            "true_positive_conditions",
            "false_positive_conditions",
        ],
        "properties": {
            "technique_description": {"type": "string", "minLength": 1},
            "data_sources": {
                "type": "array",
                "minItems": 5,
                "items": {
                    "type": "object",
                    "required": ["tool", "mode", "query_path"],
                    "properties": {
                        "tool_class": {"type": "string", "enum": ["siem", "edr", "data_lake"]},
                        "tool": {"type": "string", "minLength": 1},
                        "mode": {"enum": ["manual", "API"]},
                        "query_path": {"type": "string", "minLength": 1},
                    },
                },
            },
            "hunting_indicators": {"type": "string", "minLength": 1},
            "true_positive_conditions": {"type": "string", "minLength": 1},
            "false_positive_conditions": {"type": "string", "minLength": 1},
        },
    }


# Relative time patterns: ago(7d), now-7d, INTERVAL '7 days' - no absolute timestamps
RELATIVE_TIME_PATTERNS = ("ago(", "now-", "INTERVAL ", "interval ")
QUERY_EXTENSIONS = (".sql", ".kql", ".json")
YAML_EXTENSIONS = (".yml", ".yaml")


def _is_yaml_query_path(query_path: str) -> bool:
    """Check if query_path points to YAML format file."""
    qp = query_path.lower()
    return qp.endswith(".yml") or qp.endswith(".yaml")


def _validate_yaml_query_ids(
    playbook_dir: Path,
    data_sources: List[dict],
) -> List[str]:
    """
    Validate query_id/query_ids for YAML query_path. Require query_id or query_ids.
    Validate that each query_id exists in manual/api section of YAML file.
    Returns list of error messages.
    """
    errors: List[str] = []
    for i, entry in enumerate(data_sources):
        query_path = entry.get("query_path")
        if not query_path or not _is_yaml_query_path(query_path):
            continue
        query_id = entry.get("query_id")
        query_ids = entry.get("query_ids")
        ids: List[str] = []
        if query_ids:
            ids = list(query_ids) if isinstance(query_ids, list) else [str(q) for q in query_ids]
        elif query_id is not None:
            ids = [str(query_id)]
        else:
            errors.append(
                f"data_sources[{i}]: query_id or query_ids required for YAML query_path: {query_path}"
            )
            continue
        full_path = (playbook_dir / query_path).resolve()
        if not full_path.is_relative_to(playbook_dir) or not full_path.is_file():
            errors.append(f"data_sources[{i}]: query file not found: {query_path}")
            continue
        try:
            with open(full_path) as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            errors.append(f"data_sources[{i}]: cannot read YAML {query_path}: {e}")
            continue
        mode = entry.get("mode", "").lower()
        section = "manual" if mode == "manual" else "api"
        queries_section = data.get(section) or {}
        if not isinstance(queries_section, dict):
            errors.append(f"data_sources[{i}]: {query_path} must have {section} as dict")
            continue
        for qid in ids:
            if qid not in queries_section or not isinstance(queries_section.get(qid), dict):
                errors.append(
                    f"data_sources[{i}]: query_id '{qid}' not found in {section} in {query_path}"
                )
    return errors


def _extract_yaml_query_content(data: dict, section: str, qid: str, tool: str) -> str:
    """Extract query content from YAML block (sql, kql, or body)."""
    queries_section = data.get(section) or {}
    block = queries_section.get(qid) if isinstance(queries_section, dict) else None
    if not block or not isinstance(block, dict):
        return ""
    if tool == "elk":
        if section == "manual":
            return block.get("sql", "") or ""
        body = block.get("body")
        return json.dumps(body) if body is not None else ""
    if tool == "ms_defender":
        if section == "manual":
            return block.get("kql", "") or ""
        body = block.get("body")
        return json.dumps(body) if body is not None else ""
    content = block.get("sql") or block.get("kql")
    if content:
        return str(content)
    body = block.get("body")
    return json.dumps(body) if body is not None else ""


def _validate_query_relative_time(
    playbook_dir: Path,
    data_sources: List[dict],
) -> List[str]:
    """
    Validate that query files use relative time (e.g. ago(7d), now-7d, last 7 days)
    instead of absolute timestamps. Returns list of warning messages.
    Handles both legacy (.sql, .kql, .json) and YAML (.yml, .yaml) formats.
    """
    warnings: List[str] = []
    for entry in data_sources:
        query_path = entry.get("query_path")
        if not query_path:
            continue
        full_path = (playbook_dir / query_path).resolve()
        if not full_path.is_relative_to(playbook_dir) or not full_path.is_file():
            continue
        suffix = full_path.suffix.lower()
        contents_to_check: List[str] = []
        if suffix in YAML_EXTENSIONS:
            query_id = entry.get("query_id")
            query_ids = entry.get("query_ids")
            ids: List[str] = []
            if query_ids:
                ids = list(query_ids) if isinstance(query_ids, list) else [str(q) for q in query_ids]
            elif query_id is not None:
                ids = [str(query_id)]
            if not ids:
                continue
            try:
                with open(full_path) as f:
                    data = yaml.safe_load(f) or {}
            except Exception:
                continue
            mode = entry.get("mode", "").lower()
            section = "manual" if mode == "manual" else "api"
            tool = entry.get("tool", "")
            for qid in ids:
                content = _extract_yaml_query_content(data, section, qid, tool)
                if content:
                    contents_to_check.append(content)
        elif suffix in QUERY_EXTENSIONS:
            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
                contents_to_check.append(content)
            except OSError:
                continue
        else:
            continue
        for content in contents_to_check:
            has_relative = any(p in content for p in RELATIVE_TIME_PATTERNS)
            has_absolute = "{{timestamp_start}}" in content or "{{timestamp_end}}" in content
            if has_absolute:
                warnings.append(
                    f"Query file {query_path}: use relative time (e.g. ago(7d), last 7 days), not absolute placeholders"
                )
                break
            elif not has_relative and (".sql" in query_path or ".kql" in query_path or "sql" in content or "kql" in content):
                warnings.append(
                    f"Query file {query_path}: consider adding relative time filter (ago(7d), now-7d, INTERVAL '7 days')"
                )
                break
    return warnings


def validate_playbook(
    playbook_dir: Union[str, Path],
    schema_path: Optional[Union[str, Path]] = None,
    validate_placeholders: bool = True,
) -> ValidationResult:
    """
    Validate playbook metadata.yml.

    Checks presence of technique_description and data_sources, validates structure
    against JSON Schema. Optionally validates placeholder presence in query files.
    Returns ValidationResult with success, errors, warnings.
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
    elif len(ds) < 5:
        errors.append("data_sources must contain at least 5 queries per technique")
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
            tc = entry.get("tool_class")
            if tc is not None and tc not in ("siem", "edr", "data_lake"):
                errors.append(f"data_sources[{i}]: tool_class must be siem/edr/data_lake, got {tc!r}")
            if _is_yaml_query_path(entry.get("query_path", "")):
                qid = entry.get("query_id")
                qids = entry.get("query_ids")
                if not qid and not qids:
                    errors.append(
                        f"data_sources[{i}]: query_id or query_ids required for YAML query_path"
                    )

    # Validate query_id existence in YAML files
    if ds and not errors:
        playbook_path = Path(playbook_dir).resolve()
        yaml_errors = _validate_yaml_query_ids(playbook_path, ds)
        errors.extend(yaml_errors)

    # Optional: hypothesis, environment_requirements, operational_steps – warning if missing
    for field_name in ("hypothesis", "environment_requirements", "operational_steps"):
        val = metadata.get(field_name)
        if val is None or (isinstance(val, (list, dict)) and len(val) == 0):
            warnings.append(f"{field_name} is recommended (hypothesis, env requirements, operational steps)")

    # hunting_indicators, true_positive_conditions, false_positive_conditions – required
    for field_name in ("hunting_indicators", "true_positive_conditions", "false_positive_conditions"):
        val = metadata.get(field_name)
        if val is None:
            errors.append(f"{field_name} is required (what is searched for, TP/FP conditions)")
        elif not isinstance(val, str):
            errors.append(f"{field_name} must be a string")
        elif not str(val).strip():
            errors.append(f"{field_name} is required and must be non-empty")

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

    # Optional: validate relative time in query files (no absolute timestamps)
    if validate_placeholders and ds:
        playbook_path = Path(playbook_dir).resolve()
        time_warnings = _validate_query_relative_time(playbook_path, ds)
        for w in time_warnings:
            warnings.append(w)
            logger.warning("Query time validation: %s", w)

    logger.info("Playbook validation passed: %s", playbook_dir)
    return ValidationResult(success=True, errors=[], warnings=warnings)
