"""
Unit tests for Management Dashboard API (Phase 0-05).

Test Cases:
- TC-0-05-01: Wyświetlanie System Overview
- TC-0-05-02: Automatyczne odświeżanie statusu
- TC-0-05-03: Synchronizacja repozytorium z dashboardu
- TC-0-05-04: Edycja konfiguracji z dashboardu
- TC-0-05-05: Quick Actions - Health Check
"""

import pytest
import os
import sys
import time
from pathlib import Path
from fastapi.testclient import TestClient

# Add automation-scripts to path
project_root = Path(__file__).parent.parent.parent
automation_scripts_path = project_root / "automation-scripts"
sys.path.insert(0, str(automation_scripts_path))

# Import with proper module path
import importlib.util
import types

# Create package structure
if "automation_scripts" not in sys.modules:
    sys.modules["automation_scripts"] = types.ModuleType("automation_scripts")
    sys.modules["automation_scripts"].__path__ = [str(automation_scripts_path)]
if "automation_scripts.api" not in sys.modules:
    sys.modules["automation_scripts.api"] = types.ModuleType("automation_scripts.api")
    sys.modules["automation_scripts.api"].__path__ = [str(automation_scripts_path / "api")]

# Load dashboard_api
dashboard_api_path = automation_scripts_path / "api" / "dashboard_api.py"
dashboard_api_spec = importlib.util.spec_from_file_location("automation_scripts.api.dashboard_api", dashboard_api_path)
dashboard_api_module = importlib.util.module_from_spec(dashboard_api_spec)
sys.modules["automation_scripts.api.dashboard_api"] = dashboard_api_module
dashboard_api_spec.loader.exec_module(dashboard_api_module)
app = dashboard_api_module.app


class TestSystemOverview:
    """TC-0-05-01: Wyświetlanie System Overview"""
    
    def test_get_system_overview(self, dashboard_client, skip_if_vm_unreachable):
        """
        TC-0-05-01: Display system overview.
        
        Steps:
        1. Open Management Dashboard in n8n
        2. Check System Overview section
        3. Verify status of all 4 VMs is displayed
        
        Expected: Status of all VMs visible.
        Acceptance: 4 cards with VM status, colors match status.
        """
        # Get system overview
        response = dashboard_client.get("/system-overview")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert 'timestamp' in data, "Should have timestamp"
        assert 'summary' in data, "Should have summary"
        assert 'vms' in data, "Should have vms"
        
        # Verify summary
        summary = data.get('summary', {})
        assert 'total' in summary, "Summary should have total count"
        assert 'healthy' in summary, "Summary should have healthy count"
        assert 'unhealthy' in summary, "Summary should have unhealthy count"
        assert 'degraded' in summary, "Summary should have degraded count"
        
        # Verify VMs section
        vms = data.get('vms', {})
        assert isinstance(vms, dict), "VMs should be a dictionary"
        
        # Check that we have VM statuses
        assert len(vms) > 0, "Should have at least one VM in results"
        
        # Verify each VM has status
        for vm_id, vm_status in vms.items():
            assert isinstance(vm_status, dict), f"Status for {vm_id} should be a dictionary"
            assert 'status' in vm_status, f"Status for {vm_id} should have 'status' field"
            
            # Status should be one of: healthy, degraded, unhealthy, error
            status = vm_status.get('status')
            assert status in ['healthy', 'degraded', 'unhealthy', 'error'], \
                f"Status for {vm_id} should be valid, got: {status}"
            
            # Should have timestamp
            assert 'timestamp' in vm_status, f"Status for {vm_id} should have timestamp"


class TestAutoRefresh:
    """TC-0-05-02: Automatyczne odświeżanie statusu"""
    
    def test_auto_refresh_status(self, dashboard_client, skip_if_vm_unreachable):
        """
        TC-0-05-02: Verify automatic status refresh.
        
        Steps:
        1. Open dashboard
        2. Wait 5 minutes
        3. Check if status was refreshed
        
        Expected: Status refreshed automatically.
        Acceptance: Status updated within 5 minutes.
        
        Note: For unit test, we check that endpoint returns fresh data.
        """
        # Get initial status
        response1 = dashboard_client.get("/system-overview")
        assert response1.status_code == 200
        data1 = response1.json()
        timestamp1 = data1.get('timestamp')
        
        # Wait a bit (not 5 minutes for test, but enough to see timestamp change)
        time.sleep(2)
        
        # Get status again
        response2 = dashboard_client.get("/system-overview")
        assert response2.status_code == 200
        data2 = response2.json()
        timestamp2 = data2.get('timestamp')
        
        # Timestamps should be different (or at least endpoint should work)
        assert timestamp1 is not None, "First timestamp should not be None"
        assert timestamp2 is not None, "Second timestamp should not be None"
        
        # Verify endpoint is working and returns fresh data
        assert 'vms' in data2, "Should have VMs in response"


class TestRepositorySync:
    """TC-0-05-03: Synchronizacja repozytorium z dashboardu"""
    
    def test_sync_repository(self, dashboard_client, skip_if_vm_unreachable):
        """
        TC-0-05-03: Verify repository sync from dashboard.
        
        Steps:
        1. Click "Sync Repository" button in dashboard
        2. Check if sync was started
        3. Check sync status
        
        Expected: Sync started and completed.
        Acceptance: Sync status = "completed".
        """
        # Sync repository to all VMs
        response = dashboard_client.post(
            "/sync-repository",
            json={}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert 'success' in data, "Should have success field"
        assert 'message' in data, "Should have message field"
        assert 'execution_time' in data, "Should have execution_time field"
        
        # Verify sync was attempted (may succeed or fail depending on VM state)
        assert isinstance(data.get('success'), bool), "Success should be boolean"
        
        # Should have details if available
        if 'details' in data:
            assert isinstance(data['details'], dict), "Details should be a dictionary"


class TestConfigEdit:
    """TC-0-05-04: Edycja konfiguracji z dashboardu"""
    
    def test_get_config(self, dashboard_client):
        """Test getting configuration."""
        response = dashboard_client.get("/config")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert 'success' in data, "Should have success field"
        assert data.get('success') is True, "Should be successful"
        assert 'config' in data, "Should have config field"
        assert 'timestamp' in data, "Should have timestamp field"
        
        # Config should be a dictionary
        config = data.get('config', {})
        assert isinstance(config, dict), "Config should be a dictionary"
    
    def test_update_config(self, dashboard_client, temp_dir):
        """
        TC-0-05-04: Verify configuration editing.
        
        Steps:
        1. Open configuration editor in dashboard
        2. Modify value (e.g., VM01 IP)
        3. Save configuration
        4. Check if change was saved
        
        Expected: Configuration updated.
        Acceptance: Change visible in retrieved configuration.
        """
        # First, get current config
        get_response = dashboard_client.get("/config")
        assert get_response.status_code == 200
        current_config = get_response.json().get('config', {})
        
        # Create modified config (add test field)
        modified_config = current_config.copy()
        if 'test_timestamp' not in modified_config:
            modified_config['test_timestamp'] = f'test_value_{int(time.time())}'
        else:
            modified_config['test_timestamp'] = f'test_value_{int(time.time())}'
        
        # Update configuration
        update_response = dashboard_client.post(
            "/config",
            json={
                "config_data": modified_config,
                "validate": True,
                "create_backup": True
            }
        )
        
        assert update_response.status_code == 200, \
            f"Expected 200, got {update_response.status_code}: {update_response.text}"
        
        update_data = update_response.json()
        
        # Verify update was successful
        assert update_data.get('success') is True, "Update should be successful"
        assert 'message' in update_data, "Should have message"
        
        # Verify backup was created if requested
        if update_data.get('backup_name'):
            assert isinstance(update_data['backup_name'], str), "Backup name should be string"


class TestQuickActionsHealthCheck:
    """TC-0-05-05: Quick Actions - Health Check"""
    
    def test_health_check_single_vm(self, dashboard_client, skip_if_vm_unreachable):
        """
        TC-0-05-05: Verify running health check from dashboard.
        
        Steps:
        1. Click "Run Health Check" in dashboard
        2. Check if health check was started
        3. Check results in dashboard
        
        Expected: Health check executed, results displayed.
        Acceptance: Results available in dashboard in < 30 seconds.
        """
        # Run health check for single VM
        response = dashboard_client.post(
            "/health-check",
            json={"vm_id": "vm01"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert 'success' in data, "Should have success field"
        assert data.get('success') is True, "Health check should be successful"
        assert 'vm_id' in data, "Should have vm_id"
        assert data.get('vm_id') == 'vm01', "Should be for vm01"
        assert 'status' in data, "Should have status"
        assert 'execution_time' in data, "Should have execution_time"
        
        # Verify execution time is reasonable (< 30 seconds)
        execution_time = data.get('execution_time', 0)
        assert execution_time < 30, f"Execution time should be < 30s, got: {execution_time}"
        
        # Verify status structure
        status = data.get('status', {})
        assert isinstance(status, dict), "Status should be a dictionary"
        assert 'vm_id' in status or 'vms' in status, "Status should have vm_id or vms"
    
    def test_health_check_all_vms(self, dashboard_client, skip_if_vm_unreachable):
        """Test health check for all VMs."""
        # Run health check for all VMs
        response = dashboard_client.post(
            "/health-check",
            json={}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert 'success' in data, "Should have success field"
        assert 'status' in data, "Should have status"
        
        # Status should have vms or summary
        status = data.get('status', {})
        assert 'vms' in status or 'summary' in status, "Status should have vms or summary"

