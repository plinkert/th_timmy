"""Unit tests for config_manager (Step 0.3)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from automation_scripts.orchestrators.config_manager.config_manager import (
    get_config,
    update_config,
    backup_config,
    restore_config,
    sync_config_to_vm,
    ConfigManagerError,
    _get_remote_path,
    _get_schema_path,
)


@pytest.fixture
def miniconfig():
    return {
        "vms": {
            "vm01": {"ip": "192.168.1.1", "ssh_user": "u", "ssh_port": 22, "enabled": True},
        },
        "config_management": {
            "config_paths": {
                "central": {"default": "/opt/th_timmy/configs/central.yml"},
                "vm_specific": {
                    "vm01": "/opt/th_timmy/configs/vm01.yml",
                    "default": "/opt/th_timmy/configs/vm_specific.yml",
                },
            },
            "config_schemas": {"central": "central_config.schema.json", "vm_specific": "vm_config.schema.json"},
            "schema_dir": "configs/schemas",
        },
    }


def test_get_remote_path_default(miniconfig):
    path = _get_remote_path(miniconfig, "vm01", "central")
    assert path == "/opt/th_timmy/configs/central.yml"


def test_get_remote_path_per_vm(miniconfig):
    path = _get_remote_path(miniconfig, "vm01", "vm_specific")
    assert path == "/opt/th_timmy/configs/vm01.yml"


def test_get_remote_path_missing_config_type(miniconfig):
    with pytest.raises(ConfigManagerError):
        _get_remote_path(miniconfig, "vm01", "nonexistent")


def test_get_remote_path_missing_vm_and_default(miniconfig):
    miniconfig["config_management"]["config_paths"]["vm_specific"] = {"vm02": "/other.yml"}
    with pytest.raises(ConfigManagerError):
        _get_remote_path(miniconfig, "vm01", "vm_specific")


def test_get_schema_path(miniconfig, tmp_path):
    (tmp_path / "configs" / "schemas").mkdir(parents=True)
    (tmp_path / "configs" / "schemas" / "central_config.schema.json").write_text("{}")
    path = _get_schema_path(miniconfig, "central", repo_root=tmp_path)
    assert path is not None
    assert path.name == "central_config.schema.json"


def test_get_schema_path_missing_schema(miniconfig):
    path = _get_schema_path(miniconfig, "nonexistent", repo_root=Path.cwd())
    assert path is None or not path.is_file()


@patch("automation_scripts.orchestrators.config_manager.config_manager.download_file")
def test_get_config_success(mock_download, miniconfig):
    def write_fake_config(vm_id, remote_path, local_path, user, **kw):
        Path(local_path).write_text("config_version: '1'\ndescription: test\n")

    mock_download.side_effect = write_fake_config
    result = get_config("vm01", "central", config=miniconfig)
    assert result == {"config_version": "1", "description": "test"}
    mock_download.assert_called_once()


@patch("automation_scripts.orchestrators.config_manager.config_manager.upload_file")
@patch("automation_scripts.orchestrators.config_manager.config_manager.execute_remote_command")
def test_sync_config_to_vm_atomic(mock_exec, mock_upload, miniconfig):
    mock_exec.return_value = MagicMock(exit_code=0, stdout="", stderr="")
    sync_config_to_vm(
        "vm01",
        "central",
        {"config_version": "1"},
        config=miniconfig,
        validate=False,
        backup=False,
    )
    mock_upload.assert_called_once()
    call_kw = mock_upload.call_args
    assert call_kw[0][2].endswith(".new")
    mock_exec.assert_called_once()
    assert "mv" in mock_exec.call_args[0][1]


@patch("automation_scripts.orchestrators.config_manager.config_manager._create_backup")
@patch("automation_scripts.orchestrators.config_manager.config_manager.get_config")
@patch("automation_scripts.orchestrators.config_manager.config_manager.sync_config_to_vm")
def test_update_config_with_backup(mock_sync, mock_get, mock_backup, miniconfig):
    mock_get.return_value = {"config_version": "1"}
    mock_backup.return_value = "backup_vm01_central_20250126_120000.enc"
    mock_sync.return_value = True
    result = update_config(
        "vm01",
        "central",
        {"config_version": "1", "description": "updated"},
        config=miniconfig,
        validate=False,
        backup=True,
    )
    assert result is True
    mock_backup.assert_called_once()
    mock_sync.assert_called_once()


@patch("automation_scripts.orchestrators.config_manager.config_manager._create_backup")
@patch("automation_scripts.orchestrators.config_manager.config_manager.get_config")
@patch("automation_scripts.orchestrators.config_manager.config_manager.sync_config_to_vm")
@patch("automation_scripts.orchestrators.config_manager.config_manager._restore_backup")
def test_update_config_rollback_on_write_failure(mock_restore, mock_sync, mock_get, mock_backup, miniconfig):
    mock_get.return_value = {"config_version": "1"}
    mock_backup.return_value = "backup_vm01_central_20250126_120000.enc"
    mock_sync.side_effect = [ConfigManagerError("upload failed"), None]
    mock_restore.return_value = {"config_version": "1"}
    result = update_config(
        "vm01",
        "central",
        {"config_version": "1", "description": "updated"},
        config=miniconfig,
        validate=False,
        backup=True,
    )
    assert isinstance(result, dict)
    assert result.get("success") is False
    assert "write_failed" in result.get("error", "")
    mock_restore.assert_called_once()
    assert mock_sync.call_count == 2
