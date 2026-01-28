"""Unit tests for config_validator (Step 0.3)."""

import json
import tempfile
from pathlib import Path

import pytest

from automation_scripts.orchestrators.config_manager.config_validator import (
    validate_config,
    validate_all_required_fields,
    _load_schema,
)


@pytest.fixture
def valid_central_schema():
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "config_version": {"type": "string"},
            "description": {"type": "string"},
            "settings": {"type": "object", "additionalProperties": True},
        },
        "required": ["config_version"],
        "additionalProperties": False,
    }


@pytest.fixture
def strict_schema():
    """Schema that forbids additional properties."""
    return {
        "type": "object",
        "properties": {"name": {"type": "string"}, "port": {"type": "integer"}},
        "required": ["name"],
        "additionalProperties": False,
    }


def test_validate_config_accepts_valid_data(valid_central_schema):
    data = {"config_version": "1", "description": "test", "settings": {"a": 1}}
    ok, errs = validate_config(data, valid_central_schema)
    assert ok is True
    assert errs == []


def test_validate_config_rejects_missing_required(valid_central_schema):
    data = {"description": "no config_version"}
    ok, errs = validate_config(data, valid_central_schema)
    assert ok is False
    assert len(errs) >= 1


def test_validate_config_rejects_additional_properties(strict_schema):
    data = {"name": "ok", "extra_key": "not allowed"}
    ok, errs = validate_config(data, strict_schema)
    assert ok is False
    assert any("additional" in e.lower() or "extra" in e.lower() for e in errs)


def test_validate_config_rejects_wrong_type(strict_schema):
    data = {"name": 123}
    ok, errs = validate_config(data, strict_schema)
    assert ok is False
    assert len(errs) >= 1


def test_validate_all_required_fields_missing():
    schema = {"required": ["a", "b", "c"]}
    data = {"a": 1}
    missing = validate_all_required_fields(data, schema)
    assert set(missing) == {"b", "c"}


def test_validate_all_required_fields_none():
    schema = {}
    data = {}
    assert validate_all_required_fields(data, schema) == []


def test_load_schema_from_dict(valid_central_schema):
    loaded = _load_schema(valid_central_schema)
    assert loaded == valid_central_schema


def test_load_schema_from_json_file(valid_central_schema):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(valid_central_schema, f)
        path = f.name
    try:
        loaded = _load_schema(path)
        assert loaded["type"] == "object"
        assert "config_version" in loaded["properties"]
    finally:
        Path(path).unlink(missing_ok=True)


def test_validate_config_from_schema_file(valid_central_schema):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(valid_central_schema, f)
        path = f.name
    try:
        data = {"config_version": "1"}
        ok, errs = validate_config(data, path)
        assert ok is True
        assert errs == []
    finally:
        Path(path).unlink(missing_ok=True)


def test_validate_config_schema_file_not_found():
    with pytest.raises(FileNotFoundError):
        validate_config({"a": 1}, "/nonexistent/schema.json")
