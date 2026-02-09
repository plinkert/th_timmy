"""Unit tests for DataPackage (Step 1.5)."""

from pathlib import Path

import pytest

from automation_scripts.data_package import DataPackage, DataPackageValidationError


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _schema_path() -> Path:
    return _project_root() / "configs" / "schemas" / "data_package_schema.json"


def _valid_package_dict():
    return {
        "id": "pkg-001",
        "source": "elk",
        "timestamp": "2025-01-27T12:00:00Z",
        "data": [{"event_id": "1", "host": "vm01"}, {"event_id": "2", "host": "vm02"}],
        "anonymized": True,
        "context": {"playbook_id": "T1059", "tool": "elk"},
    }


def test_data_package_create_and_validate():
    """Valid DataPackage validates successfully."""
    dp = DataPackage(
        id="pkg-001",
        source="elk",
        timestamp="2025-01-27T12:00:00Z",
        data=[{"a": 1}, {"b": 2}],
        anonymized=True,
        context={"playbook_id": "T1059"},
    )
    assert dp.validate(schema_path=_schema_path()) is True


def test_data_package_missing_id_raises():
    """Package without id raises DataPackageValidationError."""
    dp = DataPackage(
        id="",
        source="elk",
        timestamp="2025-01-27T12:00:00Z",
        data=[],
        anonymized=True,
    )
    with pytest.raises(DataPackageValidationError) as exc:
        dp.validate(schema_path=_schema_path())
    assert "id" in str(exc.value).lower() or "minLength" in str(exc.value)


def test_data_package_data_as_string_raises():
    """from_dict with data as string raises DataPackageValidationError."""
    d = _valid_package_dict()
    d["data"] = "not a list"
    with pytest.raises(DataPackageValidationError) as exc:
        DataPackage.from_dict(d)
    assert "list" in str(exc.value).lower()


def test_data_package_data_item_string_raises():
    """data list with string item (instead of object) raises on validate."""
    dp = DataPackage(
        id="pkg-001",
        source="elk",
        timestamp="2025-01-27T12:00:00Z",
        data=[{"ok": 1}, "invalid string item"],
        anonymized=True,
    )
    with pytest.raises(DataPackageValidationError):
        dp.validate(schema_path=_schema_path())


def test_data_package_anonymized_false_accepted():
    """anonymized=false is accepted by validate (no require_anonymized_for_ai)."""
    dp = DataPackage(
        id="pkg-001",
        source="elk",
        timestamp="2025-01-27T12:00:00Z",
        data=[],
        anonymized=False,
    )
    assert dp.validate(schema_path=_schema_path()) is True


def test_data_package_require_anonymized_raises():
    """validate(require_anonymized_for_ai=True) with anonymized=False raises."""
    dp = DataPackage(
        id="pkg-001",
        source="elk",
        timestamp="2025-01-27T12:00:00Z",
        data=[],
        anonymized=False,
    )
    with pytest.raises(DataPackageValidationError) as exc:
        dp.validate(schema_path=_schema_path(), require_anonymized_for_ai=True)
    assert "anonymized" in str(exc.value).lower()


def test_data_package_to_dict_from_dict_roundtrip():
    """to_dict and from_dict roundtrip."""
    d = _valid_package_dict()
    dp = DataPackage.from_dict(d)
    out = dp.to_dict()
    assert out["id"] == d["id"]
    assert out["data"] == d["data"]
    dp2 = DataPackage.from_dict(out)
    assert dp2.id == dp.id
    assert dp2.data == dp.data


def test_data_package_from_dict_validate_on_load():
    """from_dict with validate_on_load=True validates."""
    d = _valid_package_dict()
    dp = DataPackage.from_dict(d, validate_on_load=True, schema_path=_schema_path())
    assert dp.id == "pkg-001"
    assert dp.validate(schema_path=_schema_path()) is True


def test_data_package_empty_data_accepted():
    """Empty data list [] is accepted."""
    dp = DataPackage(
        id="pkg-empty",
        source="manual",
        timestamp="2025-01-27T12:00:00Z",
        data=[],
        anonymized=True,
    )
    assert dp.validate(schema_path=_schema_path()) is True


def test_data_package_max_items_exceeded_raises():
    """More than maxItems (100000) raises on validate."""
    dp = DataPackage(
        id="pkg-big",
        source="elk",
        timestamp="2025-01-27T12:00:00Z",
        data=[{"i": i} for i in range(100001)],
        anonymized=True,
    )
    with pytest.raises(DataPackageValidationError):
        dp.validate(schema_path=_schema_path())


def test_data_package_size_limit_raises():
    """Package larger than 5 MB raises DataPackageValidationError."""
    from automation_scripts.data_package.data_package import MAX_DATA_PACKAGE_SIZE_BYTES

    # Create data that exceeds 5 MB when serialized
    large_record = {"x": "y" * 10000}  # ~10KB per record
    dp = DataPackage(
        id="pkg-huge",
        source="elk",
        timestamp="2025-01-27T12:00:00Z",
        data=[large_record] * 600,  # ~6 MB
        anonymized=True,
    )
    with pytest.raises(DataPackageValidationError) as exc:
        dp.validate(schema_path=_schema_path())
    assert "size" in str(exc.value).lower() or "exceeds" in str(exc.value).lower()


def test_data_package_to_json_from_json():
    """to_json and from_json roundtrip."""
    dp = DataPackage(
        id="pkg-json",
        source="ms_defender",
        timestamp="2025-01-27T12:00:00Z",
        data=[{"a": 1}],
        anonymized=True,
    )
    s = dp.to_json()
    assert '"id": "pkg-json"' in s
    dp2 = DataPackage.from_json(s)
    assert dp2.id == dp.id
    assert dp2.data == dp.data
