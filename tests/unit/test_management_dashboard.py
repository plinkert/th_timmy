"""Unit tests for Management Dashboard API (Step 0.5)."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from automation_scripts.playbooks.hunt_api import app


@pytest.fixture
def mock_config(tmp_path):
    """Create minimal config for dashboard tests."""
    config_yml = tmp_path / "configs" / "config.yml"
    config_yml.parent.mkdir(parents=True, exist_ok=True)
    config_yml.write_text("""
vms:
  vm01: {ip: "127.0.0.1", enabled: true}
  vm02: {ip: "127.0.0.1", enabled: true}
  vm03: {ip: "127.0.0.1", enabled: true}
  vm04: {ip: "127.0.0.1", enabled: true}
health_monitoring:
  check_interval: 300
  health_check_script_path:
    default: "/tmp/health_check.sh"
config_management:
  backup_location: "%s"
  config_paths:
    central: {default: "/tmp/central.yml"}
""" % (tmp_path / "backups"))
    return tmp_path


def test_dashboard_status_returns_vm_keys(mock_config):
    """GET /api/v1/dashboard/status returns vm01-vm04 with status and color."""
    fake_status = {
        "vm01": MagicMock(status="healthy", message="", metrics=MagicMock(
            cpu_percent=10, memory_percent=50, disk_percent=30,
            response_time_sec=0.5, uptime_sec=3600
        )),
        "vm02": MagicMock(status="warning", message="CPU > 80%", metrics=MagicMock(
            cpu_percent=85, memory_percent=60, disk_percent=40,
            response_time_sec=1.0, uptime_sec=7200
        )),
    }
    with patch.dict("os.environ", {"BOOTSTRAP_PROJECT_ROOT": str(mock_config)}):
        with patch("automation_scripts.orchestrators.health_monitor.get_health_status",
                   return_value=fake_status):
            client = TestClient(app)
            r = client.get("/api/v1/dashboard/status")
    assert r.status_code == 200
    data = r.json()
    assert "vm01" in data
    assert "vm02" in data
    assert data["vm01"]["status"] == "healthy"
    assert data["vm01"]["color"] == "green"
    assert data["vm02"]["status"] == "warning"
    assert data["vm02"]["color"] == "orange"


def test_dashboard_sync_repo_admin_ok(mock_config):
    """POST /api/v1/dashboard/sync-repo with X-User-Role: admin succeeds."""
    with patch.dict("os.environ", {"BOOTSTRAP_PROJECT_ROOT": str(mock_config)}):
        with patch("automation_scripts.orchestrators.repo_sync.sync_repository_to_all_vms") as mock_sync:
            mock_sync.return_value = {
                "vm01": MagicMock(is_synced=True, error=None, commit_hash="abc"),
                "vm02": MagicMock(is_synced=True, error=None, commit_hash="abc"),
            }
            client = TestClient(app)
            r = client.post(
                "/api/v1/dashboard/sync-repo",
                headers={"X-User-Role": "admin"},
            )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert "results" in data


def test_dashboard_sync_repo_read_only_forbidden(mock_config):
    """POST /api/v1/dashboard/sync-repo with X-User-Role: read_only returns 403."""
    with patch.dict("os.environ", {"BOOTSTRAP_PROJECT_ROOT": str(mock_config)}):
        client = TestClient(app)
        r = client.post(
            "/api/v1/dashboard/sync-repo",
            headers={"X-User-Role": "read_only"},
        )
    assert r.status_code == 403


def test_dashboard_backup_config_admin_ok(mock_config):
    """POST /api/v1/dashboard/backup-config with admin succeeds (mocked)."""
    with patch.dict("os.environ", {"BOOTSTRAP_PROJECT_ROOT": str(mock_config)}):
        with patch("automation_scripts.orchestrators.config_manager.backup_config",
                   return_value="backup_vm04_central_20250101_120000.enc"):
            client = TestClient(app)
            r = client.post(
                "/api/v1/dashboard/backup-config",
                headers={"X-User-Role": "admin"},
            )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert "backup_id" in data


def test_dashboard_refresh_hunter_ok(mock_config):
    """POST /api/v1/dashboard/refresh with X-User-Role: hunter succeeds."""
    fake_status = {"vm01": MagicMock(status="healthy", message="", metrics=None)}
    with patch.dict("os.environ", {"BOOTSTRAP_PROJECT_ROOT": str(mock_config)}):
        with patch("automation_scripts.orchestrators.health_monitor.get_health_status",
                   return_value=fake_status):
            client = TestClient(app)
            r = client.post(
                "/api/v1/dashboard/refresh",
                headers={"X-User-Role": "hunter"},
            )
    assert r.status_code == 200
    data = r.json()
    assert "vm01" in data


def test_dashboard_status_config_missing(mock_config):
    """GET /status when config.yml missing returns unknown statuses."""
    with patch.dict("os.environ", {"BOOTSTRAP_PROJECT_ROOT": str(mock_config)}):
        (mock_config / "configs" / "config.yml").unlink(missing_ok=True)
        client = TestClient(app)
        r = client.get("/api/v1/dashboard/status")
    assert r.status_code == 200
    data = r.json()
    assert data["vm01"]["status"] == "unknown"
    assert data["vm01"]["message"] == "Config not found"
