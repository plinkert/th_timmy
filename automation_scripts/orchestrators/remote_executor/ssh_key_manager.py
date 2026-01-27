"""
SSH key manager – provides private keys for VMs.

This phase: keys are read from ~/.ssh/th_timmy_keys (id_ed25519_{vm_id}).
Future: pluggable backend (Vault, encrypted dir, etc.) via get_private_key_for_vm(vm_id).
"""

from pathlib import Path
from typing import Optional, Union

import paramiko

# Default key directory (this phase, per ticket clarification)
DEFAULT_KEY_BASE = Path.home() / ".ssh" / "th_timmy_keys"
KEY_FILE_PATTERN = "id_ed25519_{vm_id}"


def get_key_base_dir(config_key_path: Optional[Union[str, Path]] = None) -> Path:
    """Return the base directory for VM keys. Config overrides default."""
    if config_key_path is not None:
        p = Path(config_key_path).expanduser().resolve()
        if p.is_dir():
            return p
    return Path(DEFAULT_KEY_BASE).expanduser().resolve()


def get_private_key_for_vm(
    vm_id: str,
    key_storage_path: Optional[Union[str, Path]] = None,
    password: Optional[str] = None,
) -> paramiko.PKey:
    """
    Load the private key for the given vm_id.

    This phase: reads from ~/.ssh/th_timmy_keys/id_ed25519_{vm_id}.
    RSA/ECDSA keys in that directory (e.g. id_rsa_vm01) can be supported by
    convention if needed.

    :param vm_id: VM identifier (e.g. vm01, vm02).
    :param key_storage_path: Optional override for key directory.
    :param password: Optional passphrase for encrypted private keys.
    :return: Loaded private key (Ed25519Key, RSAKey, or ECDSAKey).
    :raises FileNotFoundError: Key file not found.
    :raises paramiko.ssh_exception.SSHException: Invalid key or decryption failure.
    """
    base = get_key_base_dir(key_storage_path)
    # Prefer Ed25519 (matches setup_ssh_keys.sh)
    for name in (f"id_ed25519_{vm_id}", f"id_rsa_{vm_id}", f"id_ecdsa_{vm_id}"):
        path = base / name
        if path.is_file():
            if "ed25519" in name:
                return paramiko.Ed25519Key.from_private_key_file(str(path), password=password)
            return _load_rsa_or_ecdsa(path, password)
    raise FileNotFoundError(f"No private key found for vm_id={vm_id} in {base}")


def _load_rsa_or_ecdsa(path: Path, password: Optional[str]) -> paramiko.PKey:
    """Load RSA or ECDSA key from file."""
    try:
        return paramiko.RSAKey.from_private_key_file(str(path), password=password)
    except paramiko.ssh_exception.SSHException:
        return paramiko.ECDSAKey.from_private_key_file(str(path), password=password)


def get_private_key_bytes_for_vm(
    vm_id: str,
    key_storage_path: Optional[Union[str, Path]] = None,
) -> bytes:
    """
    Return raw bytes of the private key for vm_id (e.g. for use with Paramiko from buffer).
    """
    base = get_key_base_dir(key_storage_path)
    for name in (f"id_ed25519_{vm_id}", f"id_rsa_{vm_id}", f"id_ecdsa_{vm_id}"):
        path = base / name
        if path.is_file():
            return path.read_bytes()
    raise FileNotFoundError(f"No private key found for vm_id={vm_id} in {base}")
