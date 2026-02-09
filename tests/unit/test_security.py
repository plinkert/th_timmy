"""Unit tests for security module (Step 1.3)."""

import os

import pytest

from automation_scripts.security.security import (
    SecurityError,
    decrypt_mapping_value,
    encrypt_mapping_value,
    get_anonymization_secret,
)


@pytest.fixture(autouse=True)
def clear_anon_env():
    """Clear anonymization env vars before/after each test."""
    keys = [
        "TH_ANONYMIZATION_SECRET",
        "TH_ANONYMIZATION_SECRET_PATH",
        "TH_ANONYMIZATION_PASSPHRASE",
        "TH_ANONYMIZATION_MAPPING_KEY",
        "TH_ANONYMIZATION_MAPPING_KEY_PATH",
    ]
    saved = {k: os.environ.pop(k, None) for k in keys}
    yield
    for k, v in saved.items():
        if v is not None:
            os.environ[k] = v
        else:
            os.environ.pop(k, None)


def test_get_anonymization_secret_from_env():
    os.environ["TH_ANONYMIZATION_PASSPHRASE"] = "test_secret_123"
    secret = get_anonymization_secret()
    assert isinstance(secret, bytes)
    assert len(secret) == 32


def test_get_anonymization_secret_from_config():
    config = {"anonymization": {"secret": "x" * 32}}
    secret = get_anonymization_secret(config=config)
    assert len(secret) == 32
    assert secret == b"x" * 32


def test_get_anonymization_secret_raises_when_missing():
    with pytest.raises(SecurityError) as exc:
        get_anonymization_secret(config={})
    assert "No anonymization secret" in str(exc.value)


def test_encrypt_decrypt_roundtrip():
    os.environ["TH_ANONYMIZATION_PASSPHRASE"] = "encryption_test_pass"
    plain = "192.168.1.100"
    ct = encrypt_mapping_value(plain)
    assert isinstance(ct, bytes)
    assert len(ct) > 12
    dec = decrypt_mapping_value(ct)
    assert dec == plain


def test_encrypt_decrypt_with_explicit_key():
    key = b"a" * 32
    plain = "user@example.com"
    ct = encrypt_mapping_value(plain, key=key)
    dec = decrypt_mapping_value(ct, key=key)
    assert dec == plain


def test_decrypt_invalid_ciphertext_raises():
    os.environ["TH_ANONYMIZATION_PASSPHRASE"] = "test"
    with pytest.raises(SecurityError):
        decrypt_mapping_value(b"short")
    # Tampered or wrong ciphertext raises (InvalidTag or similar from cryptography)
    with pytest.raises(Exception):
        decrypt_mapping_value(b"\x00" * 12 + b"tampered" * 4)
