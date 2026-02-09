"""Unit tests for deterministic_anonymizer (Step 1.3)."""

import os

import pytest

from automation_scripts.anonymization.deterministic_anonymizer import (
    DEFAULT_PII_FIELDS,
    DeterministicAnonymizer,
    create_anonymizer,
)
from automation_scripts.anonymization.mapping_store import InMemoryMappingStore


@pytest.fixture
def secret():
    return b"test_hmac_secret_32_bytes_long!!!!"


@pytest.fixture
def anonymizer(secret):
    return DeterministicAnonymizer(secret=secret, mapping_store=InMemoryMappingStore())


def test_anonymize_deterministic(anonymizer):
    p1 = anonymizer.anonymize("192.168.1.100", "ip_address")
    p2 = anonymizer.anonymize("192.168.1.100", "ip_address")
    assert p1 == p2
    assert len(p1) == 64  # SHA256 hex
    assert p1 != "192.168.1.100"


def test_deanonymize(anonymizer):
    orig = "user@example.com"
    pseudo = anonymizer.anonymize(orig, "email")
    assert anonymizer.deanonymize(pseudo) == orig


def test_deanonymize_unknown_returns_none(anonymizer):
    assert anonymizer.deanonymize("unknown_hash_xyz") is None


def test_anonymize_empty_or_non_string_returns_unchanged(anonymizer):
    assert anonymizer.anonymize("", None) == ""
    assert anonymizer.anonymize(123, None) == 123  # type: ignore


def test_anonymize_dict(anonymizer):
    data = {"username": "alice", "ip_address": "10.0.0.1", "count": 42}
    out = anonymizer.anonymize_dict(data)
    assert out["username"] != "alice"
    assert out["ip_address"] != "10.0.0.1"
    assert out["count"] == 42
    assert anonymizer.deanonymize(out["username"]) == "alice"
    assert anonymizer.deanonymize(out["ip_address"]) == "10.0.0.1"


def test_anonymize_dict_nested(anonymizer):
    data = {"user": {"username": "bob", "email": "bob@test.com"}}
    out = anonymizer.anonymize_dict(data)
    assert out["user"]["username"] != "bob"
    assert anonymizer.deanonymize(out["user"]["username"]) == "bob"


def test_anonymize_dict_custom_fields(anonymizer):
    data = {"custom_field": "secret_value", "other": "keep"}
    out = anonymizer.anonymize_dict(data, fields={"custom_field"})
    assert out["custom_field"] != "secret_value"
    assert out["other"] == "keep"


def test_anonymize_list(anonymizer):
    items = ["ip1", "ip2", "ip1"]
    out = anonymizer.anonymize_list(items, field_type="ip")
    assert len(out) == 3
    assert out[0] == out[2]  # same input → same output
    assert out[0] != "ip1"
    assert anonymizer.deanonymize(out[0]) == "ip1"


def test_create_anonymizer_with_env():
    os.environ["TH_ANONYMIZATION_PASSPHRASE"] = "factory_test_pass"
    try:
        anon = create_anonymizer()
        p = anon.anonymize("test_value", None)
        assert len(p) == 64
        assert anon.deanonymize(p) == "test_value"
    finally:
        os.environ.pop("TH_ANONYMIZATION_PASSPHRASE", None)


def test_create_anonymizer_with_db_path(tmp_path):
    os.environ["TH_ANONYMIZATION_PASSPHRASE"] = "db_test"
    try:
        db = tmp_path / "anon.db"
        anon = create_anonymizer(db_path=db)
        anon.anonymize("persisted", "test")
        anon2 = create_anonymizer(db_path=db)
        # Same secret, so same pseudonym; store has mapping
        p = anon2.anonymize("persisted", "test")
        assert anon2.deanonymize(p) == "persisted"
    finally:
        os.environ.pop("TH_ANONYMIZATION_PASSPHRASE", None)


def test_secret_too_short_raises():
    with pytest.raises(ValueError):
        DeterministicAnonymizer(secret=b"short", mapping_store=InMemoryMappingStore())
