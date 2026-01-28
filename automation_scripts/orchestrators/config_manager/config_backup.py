"""
Configuration backup – encrypted backups with retention.

Creates encrypted backups (AES-256-GCM) in backup_location; enforces retention
(min 90 days). Optional copy to backup_remote_path if configured.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
import yaml


class BackupError(Exception):
    """Raised on backup/restore/list failures."""

    pass


def _get_backup_key(config: dict) -> bytes:
    """
    Derive or load AES key from config.
    Prefer env var TH_TIMMY_CONFIG_BACKUP_KEY or config_management.encryption_key_path.
    Key must be 32 bytes for AES-256 (or we derive from passphrase via Scrypt).
    """
    cm = config.get("config_management") or {}
    key_path = cm.get("encryption_key_path") or os.environ.get("TH_TIMMY_CONFIG_BACKUP_KEY_PATH")
    if key_path:
        path = Path(key_path).expanduser().resolve()
        if path.is_file():
            key = path.read_bytes().strip()
            if len(key) == 32:
                return key
            # Treat as passphrase and derive
            return _derive_key(key)
    passphrase = os.environ.get("TH_TIMMY_CONFIG_BACKUP_PASSPHRASE", "").encode("utf-8")
    if not passphrase:
        raise BackupError(
            "No backup encryption key: set TH_TIMMY_CONFIG_BACKUP_PASSPHRASE or "
            "config_management.encryption_key_path / TH_TIMMY_CONFIG_BACKUP_KEY_PATH"
        )
    return _derive_key(passphrase)


def _derive_key(passphrase: bytes) -> bytes:
    """Derive 32-byte key from passphrase using Scrypt."""
    salt = b"th_timmy_config_backup_v1"
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    return kdf.derive(passphrase)


def _load_config(config_path: Optional[Union[str, Path]] = None) -> dict:
    path = config_path or Path.cwd() / "configs" / "config.yml"
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _config_management_settings(config: dict) -> dict:
    cm = config.get("config_management") or {}
    return {
        "backup_location": (cm.get("backup_location") or "/var/backups/th_timmy/config").strip(),
        "backup_retention_days": max(90, int(cm.get("backup_retention_days", 90))),
        "encryption_method": cm.get("encryption_method", "AES"),
        "encryption_key_path": cm.get("encryption_key_path"),
        "backup_remote_path": cm.get("backup_remote_path") or "",
    }


def _ensure_backup_dir(backup_location: Union[str, Path]) -> Path:
    p = Path(backup_location).expanduser().resolve()
    try:
        p.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        raise BackupError(
            f"Cannot create backup directory '{p}' (permission denied). "
            "Use a path writable by the current user (e.g. under project or home), "
            "or run with elevated privileges (e.g. sudo) when using system paths like /var/backups."
        ) from e
    return p


def _encrypt(data: bytes, key: bytes) -> bytes:
    """Encrypt with AES-256-GCM; prepend 12-byte nonce."""
    aes = AESGCM(key)
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, data, None)
    return nonce + ct


def _decrypt(data: bytes, key: bytes) -> bytes:
    """Decrypt payload (nonce + ciphertext)."""
    if len(data) < 12:
        raise BackupError("Invalid backup payload: too short")
    aes = AESGCM(key)
    return aes.decrypt(data[:12], data[12:], None)


def create_backup(
    vm_id: str,
    config_type: str,
    config_data: Union[dict, str],
    *,
    config_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
    **kwargs: Any,
) -> str:
    """
    Create encrypted backup of config_data; store in backup_location.
    Purge backups older than backup_retention_days.
    Returns backup_id (filename).
    """
    cfg = config or _load_config(config_path)
    opts = _config_management_settings(cfg)
    if opts["encryption_method"] != "AES":
        raise BackupError("Only encryption_method 'AES' is supported in this implementation")
    key = _get_backup_key(cfg)
    backup_dir = _ensure_backup_dir(opts["backup_location"])
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_id = f"backup_{vm_id}_{config_type}_{ts}.enc"
    path = backup_dir / backup_id
    if isinstance(config_data, dict):
        payload = json.dumps(config_data, sort_keys=True).encode("utf-8")
    else:
        payload = config_data.encode("utf-8") if isinstance(config_data, str) else config_data
    encrypted = _encrypt(payload, key)
    path.write_bytes(encrypted)
    # Optional: copy to backup_remote_path (SCP/SFTP not implemented here; placeholder)
    _purge_old_backups(backup_dir, opts["backup_retention_days"])
    return backup_id


def restore_backup(
    backup_id: str,
    *,
    config_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
    **kwargs: Any,
) -> dict:
    """
    Restore config data from backup by backup_id.
    Returns config_data as dict (assumes JSON content was backed up).
    """
    cfg = config or _load_config(config_path)
    opts = _config_management_settings(cfg)
    key = _get_backup_key(cfg)
    backup_dir = Path(opts["backup_location"]).expanduser().resolve()
    path = backup_dir / backup_id
    if not path.is_file():
        raise BackupError(f"Backup not found: {backup_id}")
    raw = path.read_bytes()
    decrypted = _decrypt(raw, key)
    try:
        return json.loads(decrypted.decode("utf-8"))
    except json.JSONDecodeError:
        return {"_raw": decrypted.decode("utf-8", errors="replace")}


def list_backups(
    vm_id: Optional[str] = None,
    config_type: Optional[str] = None,
    *,
    config_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
    **kwargs: Any,
) -> List[dict]:
    """
    List backups with metadata (backup_id, vm_id, config_type, timestamp, size).
    Filter by vm_id and/or config_type (prefix match on filename).
    """
    cfg = config or _load_config(config_path)
    opts = _config_management_settings(cfg)
    backup_dir = Path(opts["backup_location"]).expanduser().resolve()
    if not backup_dir.is_dir():
        return []
    result = []
    prefix = "backup_"
    for f in backup_dir.iterdir():
        if not f.is_file() or not f.name.startswith(prefix) or not f.name.endswith(".enc"):
            continue
        name = f.name
        inner = name[len(prefix) : -4]  # vm01_vm_specific_20250126_120000
        parts = inner.split("_")
        if len(parts) < 4:
            continue
        b_vm = parts[0]
        b_ts = "_".join(parts[-2:])
        b_type = "_".join(parts[1:-2])
        if vm_id is not None and b_vm != vm_id:
            continue
        if config_type is not None and b_type != config_type:
            continue
        try:
            stat = f.stat()
            result.append({
                "backup_id": name,
                "vm_id": b_vm,
                "config_type": b_type,
                "timestamp": b_ts,
                "size": stat.st_size,
            })
        except OSError:
            continue
    result.sort(key=lambda x: x["timestamp"], reverse=True)
    return result


def _purge_old_backups(backup_dir: Path, retention_days: int) -> None:
    """Remove backup files older than retention_days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    for f in backup_dir.iterdir():
        if not f.is_file() or not f.name.startswith("backup_") or not f.name.endswith(".enc"):
            continue
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                f.unlink()
        except OSError:
            pass
