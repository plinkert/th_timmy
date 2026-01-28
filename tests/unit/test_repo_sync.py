"""Unit tests for repo_sync (sync_repository_to_vm, check_repo_status, verify_sync)."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from automation_scripts.orchestrators.repo_sync import (
    RepoStatus,
    sync_repository_to_vm,
    sync_repository_to_all_vms,
    check_repo_status,
    verify_sync,
)
from automation_scripts.orchestrators.repo_sync.secret_scanner import SecretScanResult
from automation_scripts.orchestrators.repo_sync.repo_sync import (
    _target_vm_ids,
    _repository_settings,
    _get_vm_connection_params,
)


@pytest.fixture
def miniconfig():
    return {
        "vms": {
            "vm01": {"ip": "192.168.1.1", "ssh_user": "u", "ssh_port": 22, "enabled": True},
            "vm02": {"ip": "192.168.1.2", "ssh_user": "u", "ssh_port": 22, "enabled": True},
            "vm04": {"ip": "192.168.1.4", "ssh_user": "u", "ssh_port": 22, "enabled": True},
        },
        "repository": {
            "main_repo_path": "/opt/th_timmy",
            "vm_repo_paths": {"vm01": "/home/u/th_timmy", "vm02": "/home/u/th_timmy", "vm04": "/opt/th_timmy"},
            "default_branch": "main",
            "rsync_excludes": [".git", "__pycache__"],
            "exclude_dot_git": True,
        },
        "remote_execution": {"key_storage_path": "~/.ssh/th_timmy_keys"},
    }


def test_target_vm_ids_excludes_vm04(miniconfig):
    """_target_vm_ids returns vm01, vm02 (not vm04) when push_targets not set."""
    ids = _target_vm_ids(miniconfig)
    assert "vm04" not in ids
    assert "vm01" in ids
    assert "vm02" in ids


def test_target_vm_ids_uses_push_targets(miniconfig):
    """_target_vm_ids uses repository.push_targets when set."""
    miniconfig["repository"]["push_targets"] = ["vm01"]
    assert _target_vm_ids(miniconfig) == ["vm01"]


def test_repository_settings_defaults(miniconfig):
    """_repository_settings returns main_repo_path, vm_repo_paths, default_branch, etc."""
    opts = _repository_settings(miniconfig)
    assert opts["main_repo_path"] == "/opt/th_timmy"
    assert opts["vm_repo_paths"]["vm01"] == "/home/u/th_timmy"
    assert opts["default_branch"] == "main"
    assert opts["exclude_dot_git"] is True


def test_get_vm_connection_params(miniconfig):
    """_get_vm_connection_params returns host, port, username from vms."""
    p = _get_vm_connection_params(miniconfig, "vm01")
    assert p["host"] == "192.168.1.1"
    assert p["port"] == 22
    assert p["username"] == "u"


def test_sync_repository_to_vm_main_path_not_dir(miniconfig):
    """sync_repository_to_vm returns error RepoStatus when main_repo_path is not a directory."""
    miniconfig["repository"]["main_repo_path"] = "/nonexistent/path"
    with patch("automation_scripts.orchestrators.repo_sync.repo_sync._load_config", return_value=miniconfig):
        st = sync_repository_to_vm("vm01", config=miniconfig)
    assert st.is_synced is False
    assert st.error is not None
    assert "not a directory" in (st.error or "")


def test_sync_repository_to_vm_blocked_by_secrets(miniconfig, tmp_path):
    """sync_repository_to_vm returns error when secret scan finds secrets and block_on_secrets=True."""
    miniconfig["repository"]["main_repo_path"] = str(tmp_path)
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / "dummy").touch()
    with patch("automation_scripts.orchestrators.repo_sync.repo_sync._load_config", return_value=miniconfig):
        with patch(
            "automation_scripts.orchestrators.repo_sync.repo_sync.scan_repository",
            return_value=SecretScanResult(has_secrets=True, secrets_found=[{"file": "x"}], scan_timestamp=""),
        ):
            st = sync_repository_to_vm("vm01", config=miniconfig, run_secret_scan=True, block_on_secrets=True)
    assert st.is_synced is False
    assert "secrets" in (st.error or "").lower()


def test_sync_repository_to_vm_success_skips_rsync_with_mock(miniconfig, tmp_path):
    """sync_repository_to_vm returns RepoStatus with is_synced=True when git pull and rsync succeed."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    miniconfig["repository"]["main_repo_path"] = str(repo)
    miniconfig["repository"]["vm_repo_paths"]["vm01"] = "/remote/th_timmy"

    with patch("automation_scripts.orchestrators.repo_sync.repo_sync._load_config", return_value=miniconfig):
        with patch(
            "automation_scripts.orchestrators.repo_sync.repo_sync.scan_repository",
            return_value=SecretScanResult(has_secrets=False, secrets_found=[], scan_timestamp=""),
        ):
            with patch("automation_scripts.orchestrators.repo_sync.repo_sync.GitManager") as GM:
                gm = MagicMock()
                gm.get_commit_hash.return_value = "abc123"
                GM.return_value = gm
                with patch("automation_scripts.orchestrators.repo_sync.repo_sync._run_rsync", return_value=(True, "")):
                    st = sync_repository_to_vm("vm01", config=miniconfig, run_secret_scan=True)
    assert st.is_synced is True
    assert st.commit_hash == "abc123"
    assert st.vm_id == "vm01"


def test_check_repo_status_calls_execute_remote_command(miniconfig):
    """check_repo_status uses execute_remote_command to read .sync_rev on target."""
    miniconfig["repository"]["main_repo_path"] = "/opt/th_timmy"
    with patch("automation_scripts.orchestrators.repo_sync.repo_sync._load_config", return_value=miniconfig):
        with patch("automation_scripts.orchestrators.repo_sync.repo_sync.GitManager") as GM:
            gm = MagicMock()
            gm.get_commit_hash.return_value = "abc123"
            GM.return_value = gm
            with patch(
                "automation_scripts.orchestrators.repo_sync.repo_sync.execute_remote_command",
                return_value=MagicMock(stdout="abc123\n", success=True),
            ):
                st = check_repo_status("vm01", config=miniconfig)
    assert st.is_synced is True
    assert st.commit_hash == "abc123"


def test_verify_sync_true_when_all_match(miniconfig):
    """verify_sync returns True when all targets have same hash as VM04."""
    miniconfig["repository"]["main_repo_path"] = "/opt/th_timmy"
    with patch("automation_scripts.orchestrators.repo_sync.repo_sync._load_config", return_value=miniconfig):
        with patch("automation_scripts.orchestrators.repo_sync.repo_sync.check_repo_status") as cs:
            cs.return_value = RepoStatus("vm01", "main", "abc123", True, "", "n/a")
            out = verify_sync(expected_commit="abc123", config=miniconfig)
    assert out is True


def test_verify_sync_false_when_one_mismatches(miniconfig):
    """verify_sync returns False when any target has different hash."""
    miniconfig["repository"]["main_repo_path"] = "/opt/th_timmy"
    call_count = [0]

    def side_effect(vm_id, **kwargs):
        call_count[0] += 1
        return RepoStatus(vm_id, "main", "abc123" if vm_id == "vm01" else "other", vm_id == "vm01", "", "n/a")

    with patch("automation_scripts.orchestrators.repo_sync.repo_sync._load_config", return_value=miniconfig):
        with patch("automation_scripts.orchestrators.repo_sync.repo_sync.check_repo_status", side_effect=side_effect):
            out = verify_sync(expected_commit="abc123", config=miniconfig)
    assert out is False
