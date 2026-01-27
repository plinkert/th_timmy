"""Unit tests for ssh_key_manager."""

import tempfile
from pathlib import Path

import pytest

from automation_scripts.orchestrators.remote_executor.ssh_key_manager import (
    get_key_base_dir,
    get_private_key_for_vm,
    get_private_key_bytes_for_vm,
)


def _make_ed25519_key_file(path: Path) -> None:
    """Write a new Ed25519 private key to path (OpenSSH format). Paramiko 4.x has no Ed25519Key.generate()."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519
    pk = ed25519.Ed25519PrivateKey.generate()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        pk.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.OpenSSH,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )


def test_get_key_base_dir_default():
    """get_key_base_dir returns ~/.ssh/th_timmy_keys when no config path."""
    d = get_key_base_dir(None)
    assert "th_timmy_keys" in str(d)
    assert d.is_dir() or not d.exists()  # may not exist yet


def test_get_key_base_dir_override(tmp_path):
    """get_key_base_dir uses config path when provided and is dir."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    d = get_key_base_dir(str(tmp_path))
    assert d == tmp_path.resolve()


def test_get_private_key_for_vm_not_found():
    """get_private_key_for_vm raises FileNotFoundError when no key exists."""
    with tempfile.TemporaryDirectory() as td:
        with pytest.raises(FileNotFoundError) as exc:
            get_private_key_for_vm("vm99", key_storage_path=td)
        assert "vm99" in str(exc.value)


def test_get_private_key_for_vm_ed25519(tmp_path):
    """get_private_key_for_vm loads Ed25519 key from id_ed25519_{vm_id}."""
    key_path = tmp_path / "id_ed25519_vm01"
    _make_ed25519_key_file(key_path)
    pkey = get_private_key_for_vm("vm01", key_storage_path=str(tmp_path))
    assert pkey is not None
    assert hasattr(pkey, "get_name")
