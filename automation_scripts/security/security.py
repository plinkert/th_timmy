"""
Security utilities for deterministic anonymization (Step 1.3).

- get_anonymization_secret: HMAC key for pseudonymization (from env/config)
- encrypt_mapping_value / decrypt_mapping_value: AES-256-GCM for mapping storage
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional, Union

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

import logging

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Raised on security-related failures (missing secret, invalid key, etc.)."""

    pass


def get_anonymization_secret(
    config: Optional[dict] = None,
    config_path: Optional[Union[str, Path]] = None,
) -> bytes:
    """
    Get HMAC secret for deterministic anonymization.

    Priority:
    1. TH_ANONYMIZATION_SECRET (env) – raw secret or base64
    2. anonymization.secret_path (config) – path to key file
    3. TH_ANONYMIZATION_SECRET_PATH (env) – path to key file
    4. anonymization.secret (config) – fallback (not recommended in prod)
    5. TH_ANONYMIZATION_PASSPHRASE (env) – derive key via Scrypt

    Returns 32-byte key suitable for HMAC-SHA256.
    """
    cfg = config or _load_config(config_path)
    anon = (cfg or {}).get("anonymization") or {}

    # 1. Direct env secret (base64 or raw)
    env_secret = os.environ.get("TH_ANONYMIZATION_SECRET")
    if env_secret:
        try:
            import base64
            raw = base64.b64decode(env_secret)
            if len(raw) >= 32:
                return raw[:32]
            return _derive_key(raw)
        except Exception:
            pass
        # Treat as raw string
        b = env_secret.encode("utf-8")
        return b[:32].ljust(32, b"\0") if len(b) < 32 else b[:32]

    # 2. Key file from config or env
    key_path = anon.get("secret_path") or os.environ.get("TH_ANONYMIZATION_SECRET_PATH")
    if key_path:
        p = Path(key_path).expanduser().resolve()
        if p.is_file():
            key = p.read_bytes().strip()
            if len(key) >= 32:
                return key[:32]
            return _derive_key(key)

    # 3. Config secret (dev only)
    cfg_secret = anon.get("secret")
    if cfg_secret:
        b = cfg_secret.encode("utf-8") if isinstance(cfg_secret, str) else cfg_secret
        return b[:32].ljust(32, b"\0") if len(b) < 32 else b[:32]

    # 4. Passphrase from env
    passphrase = os.environ.get("TH_ANONYMIZATION_PASSPHRASE", "").encode("utf-8")
    if passphrase:
        return _derive_key(passphrase)

    raise SecurityError(
        "No anonymization secret: set TH_ANONYMIZATION_SECRET, "
        "TH_ANONYMIZATION_SECRET_PATH, TH_ANONYMIZATION_PASSPHRASE, "
        "or anonymization.secret_path / anonymization.secret in config"
    )


def _derive_key(passphrase: bytes) -> bytes:
    """Derive 32-byte key from passphrase using Scrypt."""
    salt = b"th_timmy_anonymization_v1"
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    return kdf.derive(passphrase)


def _load_config(config_path: Optional[Union[str, Path]] = None) -> dict:
    path = config_path or Path.cwd() / "configs" / "config.yml"
    path = Path(path).resolve()
    if not path.is_file():
        return {}
    try:
        import yaml
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def get_mapping_encryption_key(
    config: Optional[dict] = None,
    config_path: Optional[Union[str, Path]] = None,
) -> bytes:
    """
    Get AES-256 key for encrypting mapping values.

    Uses same sources as get_anonymization_secret, but can be overridden by
    anonymization.mapping_encryption_key_path or TH_ANONYMIZATION_MAPPING_KEY.
    """
    cfg = config or _load_config(config_path)
    anon = (cfg or {}).get("anonymization") or {}

    env_key = os.environ.get("TH_ANONYMIZATION_MAPPING_KEY")
    if env_key:
        try:
            import base64
            raw = base64.b64decode(env_key)
            if len(raw) >= 32:
                return raw[:32]
        except Exception:
            pass
        b = env_key.encode("utf-8")
        return b[:32].ljust(32, b"\0") if len(b) < 32 else b[:32]

    key_path = anon.get("mapping_encryption_key_path") or os.environ.get(
        "TH_ANONYMIZATION_MAPPING_KEY_PATH"
    )
    if key_path:
        p = Path(key_path).expanduser().resolve()
        if p.is_file():
            key = p.read_bytes().strip()
            if len(key) >= 32:
                return key[:32]
            return _derive_key(key)

    # Fall back to anonymization secret (same key for HMAC and mapping encryption)
    return get_anonymization_secret(config=cfg, config_path=config_path)


def encrypt_mapping_value(
    plaintext: str,
    *,
    config: Optional[dict] = None,
    config_path: Optional[Union[str, Path]] = None,
    key: Optional[bytes] = None,
) -> bytes:
    """
    Encrypt a mapping value (original or pseudonym) with AES-256-GCM.

    Returns: nonce (12 bytes) + ciphertext.
    """
    k = key or get_mapping_encryption_key(config=config, config_path=config_path)
    if len(k) != 32:
        raise SecurityError("Encryption key must be 32 bytes")
    aes = AESGCM(k)
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, plaintext.encode("utf-8"), None)
    return nonce + ct


def decrypt_mapping_value(
    ciphertext: bytes,
    *,
    config: Optional[dict] = None,
    config_path: Optional[Union[str, Path]] = None,
    key: Optional[bytes] = None,
) -> str:
    """
    Decrypt a mapping value encrypted with encrypt_mapping_value.
    """
    if len(ciphertext) < 12:
        raise SecurityError("Invalid ciphertext: too short")
    k = key or get_mapping_encryption_key(config=config, config_path=config_path)
    if len(k) != 32:
        raise SecurityError("Decryption key must be 32 bytes")
    aes = AESGCM(k)
    plain = aes.decrypt(ciphertext[:12], ciphertext[12:], None)
    return plain.decode("utf-8")
