"""Unit tests for config_backup (Step 0.3)."""

import os
import tempfile
from pathlib import Path

import pytest

from automation_scripts.orchestrators.config_manager.config_backup import (
    create_backup,
    restore_backup,
    list_backups,
    BackupError,
    _purge_old_backups,
)


@pytest.fixture
def backup_config(tmp_path):
    """Config with temp backup_location and passphrase for tests."""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    return {
        "config_management": {
            "backup_location": str(backup_dir),
            "backup_retention_days": 90,
            "encryption_method": "AES",
            "encryption_key_path": None,
        },
    }


@pytest.fixture(autouse=True)
def set_backup_passphrase():
    """Set env passphrase so _get_backup_key works in tests."""
    orig = os.environ.get("TH_TIMMY_CONFIG_BACKUP_PASSPHRASE")
    os.environ["TH_TIMMY_CONFIG_BACKUP_PASSPHRASE"] = "test_passphrase_for_unit_tests_only"
    yield
    if orig is not None:
        os.environ["TH_TIMMY_CONFIG_BACKUP_PASSPHRASE"] = orig
    else:
        os.environ.pop("TH_TIMMY_CONFIG_BACKUP_PASSPHRASE", None)


def test_create_backup_restore_backup_roundtrip(backup_config):
    data = {"config_version": "1", "name": "vm01", "port": 5432}
    backup_id = create_backup("vm01", "central", data, config=backup_config)
    assert backup_id.endswith(".enc")
    assert "vm01" in backup_id and "central" in backup_id
    restored = restore_backup(backup_id, config=backup_config)
    assert restored == data


def test_create_backup_list_backups(backup_config):
    create_backup("vm01", "vm_specific", {"vm_id": "vm01"}, config=backup_config)
    create_backup("vm02", "vm_specific", {"vm_id": "vm02"}, config=backup_config)
    all_backups = list_backups(config=backup_config)
    assert len(all_backups) >= 2
    by_vm = [b for b in all_backups if b["vm_id"] == "vm01"]
    assert len(by_vm) >= 1
    assert by_vm[0]["config_type"] == "vm_specific"
    assert "backup_id" in by_vm[0]
    assert "timestamp" in by_vm[0]
    assert "size" in by_vm[0]


def test_list_backups_filter_by_vm_id(backup_config):
    create_backup("vm01", "central", {"a": 1}, config=backup_config)
    create_backup("vm02", "central", {"b": 2}, config=backup_config)
    only_vm01 = list_backups(vm_id="vm01", config=backup_config)
    assert all(b["vm_id"] == "vm01" for b in only_vm01)


def test_list_backups_filter_by_config_type(backup_config):
    create_backup("vm01", "central", {"a": 1}, config=backup_config)
    create_backup("vm01", "env", {"KEY": "val"}, config=backup_config)
    only_central = list_backups(config_type="central", config=backup_config)
    assert all(b["config_type"] == "central" for b in only_central)


def test_restore_backup_not_found(backup_config):
    with pytest.raises(BackupError):
        restore_backup("backup_nonexistent_central_20000101_000000.enc", config=backup_config)


def test_create_backup_requires_key_or_passphrase(tmp_path):
    config_no_key = {
        "config_management": {
            "backup_location": str(tmp_path),
            "encryption_method": "AES",
        },
    }
    orig = os.environ.pop("TH_TIMMY_CONFIG_BACKUP_PASSPHRASE", None)
    try:
        with pytest.raises(BackupError):
            create_backup("vm01", "central", {"a": 1}, config=config_no_key)
    finally:
        if orig is not None:
            os.environ["TH_TIMMY_CONFIG_BACKUP_PASSPHRASE"] = orig
