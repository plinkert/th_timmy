"""Unit tests for remote_executor (execute_remote_command, vm_id validation, result shape)."""

from unittest.mock import MagicMock, patch

import pytest

from automation_scripts.orchestrators.remote_executor import (
    execute_remote_command,
    RemoteExecutionResult,
    upload_file,
    download_file,
)
from automation_scripts.orchestrators.remote_executor.remote_executor import (
    _allowed_vm_ids,
    _get_vm_connection_params,
    _load_config,
    _sha256_local,
)


@pytest.fixture
def miniconfig():
    return {
        "vms": {
            "vm01": {"ip": "192.168.1.1", "ssh_user": "u", "ssh_port": 22, "enabled": True},
        },
        "remote_execution": {"default_timeout": 30, "default_retry": 2},
    }


def test_allowed_vm_ids_from_vms(miniconfig):
    """_allowed_vm_ids returns vm ids with enabled=true from vms."""
    assert "vm01" in _allowed_vm_ids(miniconfig)


def test_allowed_vm_ids_from_remote_execution(miniconfig):
    """_allowed_vm_ids uses remote_execution.allowed_vm_ids when present."""
    miniconfig["remote_execution"]["allowed_vm_ids"] = ["vm02"]
    assert _allowed_vm_ids(miniconfig) == ["vm02"]


def test_get_vm_connection_params(miniconfig):
    """_get_vm_connection_params returns host, port, username."""
    p = _get_vm_connection_params(miniconfig, "vm01")
    assert p["host"] == "192.168.1.1"
    assert p["port"] == 22
    assert p["username"] == "u"


def test_get_vm_connection_params_missing_vm(miniconfig):
    """_get_vm_connection_params raises ValueError for unknown vm_id."""
    with pytest.raises(ValueError):
        _get_vm_connection_params(miniconfig, "vm99")


def test_sha256_local(tmp_path):
    """_sha256_local returns hex digest of file."""
    f = tmp_path / "f.txt"
    f.write_text("hello")
    import hashlib
    expected = hashlib.sha256(b"hello").hexdigest()
    assert _sha256_local(f) == expected


@patch("automation_scripts.orchestrators.remote_executor.remote_executor.get_private_key_for_vm")
@patch("automation_scripts.orchestrators.remote_executor.remote_executor.SSHClient")
def test_execute_remote_command_success(mock_ssh_class, mock_get_key, miniconfig):
    """execute_remote_command returns RemoteExecutionResult with stdout, exit_code, execution_time."""
    mock_get_key.return_value = MagicMock()
    mock_client = MagicMock()
    mock_client.execute.return_value = ("out", "err", 0)
    mock_ssh_class.return_value = mock_client

    result = execute_remote_command(
        "vm01", "echo hi", "user1", 10.0, config=miniconfig, retries=1,
    )
    assert isinstance(result, RemoteExecutionResult)
    assert result.stdout == "out"
    assert result.stderr == "err"
    assert result.exit_code == 0
    assert result.success is True
    assert result.vm_id == "vm01"
    assert result.command == "echo hi"
    assert result.execution_time >= 0


def test_execute_remote_command_vm_id_not_allowed(miniconfig):
    """execute_remote_command raises ValueError when vm_id not in allowed list."""
    with pytest.raises(ValueError) as exc:
        execute_remote_command("vm99", "echo hi", "user1", 10.0, config=miniconfig)
    assert "vm99" in str(exc.value)
