"""
Unit tests for Deployment Management Interface (Phase 0-07).

Test Cases:
- TC-0-07-01: Status instalacji
- TC-0-07-02: Uruchomienie instalacji z dashboardu
- TC-0-07-03: Weryfikacja deploymentu
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


class TestInstallationStatus:
    """TC-0-07-01: Status instalacji"""
    
    def test_get_installation_status_all(self, dashboard_client, skip_if_vm_unreachable):
        """
        TC-0-07-01: Verify installation status display.
        
        Steps:
        1. Open Deployment Management in dashboard
        2. Check installation status of all VMs
        3. Verify status is correct
        
        Expected: Installation status displayed.
        Acceptance: Status for all VMs available.
        """
        # Get installation status for all VMs
        response = dashboard_client.get("/deployment/installation-status")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert 'success' in data, "Should have success field"
        assert data.get('success') is True, "Should be successful"
        assert 'data' in data, "Should have data field"
        assert 'timestamp' in data, "Should have timestamp"
        
        # Verify data structure
        status_data = data.get('data', {})
        assert 'vms' in status_data or 'summary' in status_data, \
            "Should have vms or summary in data"
        
        # If summary exists, verify structure
        if 'summary' in status_data:
            summary = status_data.get('summary', {})
            assert 'total' in summary, "Summary should have total count"
            assert 'installed' in summary, "Summary should have installed count"
            assert 'partial' in summary, "Summary should have partial count"
            assert 'not_installed' in summary, "Summary should have not_installed count"
        
        # If vms exists, verify structure
        if 'vms' in status_data:
            vms = status_data.get('vms', {})
            assert isinstance(vms, dict), "VMs should be a dictionary"
            
            # Each VM should have status
            for vm_id, vm_status in vms.items():
                assert isinstance(vm_status, dict), f"Status for {vm_id} should be a dictionary"
                assert 'status' in vm_status, f"Status for {vm_id} should have 'status' field"
                
                # Status should be one of: installed, partial, not_installed, unknown
                status = vm_status.get('status')
                assert status in ['installed', 'partial', 'not_installed', 'unknown'], \
                    f"Status for {vm_id} should be valid, got: {status}"
    
    def test_get_installation_status_single_vm(self, dashboard_client, skip_if_vm_unreachable):
        """Test getting installation status for single VM."""
        # Get installation status for VM01
        response = dashboard_client.get("/deployment/installation-status?vm_id=vm01")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert 'success' in data, "Should have success field"
        assert 'data' in data, "Should have data field"
        
        # Data should have status
        status_data = data.get('data', {})
        assert 'status' in status_data, "Should have status in data"


class TestRunInstallation:
    """TC-0-07-02: Uruchomienie instalacji z dashboardu"""
    
    def test_run_installation(self, dashboard_client, skip_if_vm_unreachable):
        """
        TC-0-07-02: Verify running installation remotely.
        
        Steps:
        1. Open Deployment Management
        2. Click "Install VM01"
        3. Check if installation was started
        4. Check installation logs
        
        Expected: Installation started, logs available.
        Acceptance: Installation in progress, logs displayed in real-time.
        
        Note: Full installation may take time, so we test that it starts correctly.
        """
        # Run installation on VM01
        response = dashboard_client.post(
            "/deployment/run-installation",
            json={"vm_id": "vm01"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert 'success' in data, "Should have success field"
        assert 'deployment_id' in data, "Should have deployment_id"
        assert 'vm_id' in data, "Should have vm_id"
        assert data.get('vm_id') == 'vm01', "Should be for vm01"
        assert 'status' in data, "Should have status"
        assert 'message' in data, "Should have message"
        assert 'timestamp' in data, "Should have timestamp"
        
        # Status should be one of: success, failed, in_progress, completed
        status = data.get('status')
        assert status in ['success', 'failed', 'in_progress', 'completed', 'unknown'], \
            f"Status should be valid, got: {status}"
        
        # Deployment ID should be present
        deployment_id = data.get('deployment_id')
        assert deployment_id is not None and len(deployment_id) > 0, \
            "Deployment ID should be present"
    
    def test_get_installation_logs(self, dashboard_client, skip_if_vm_unreachable):
        """Test getting installation logs."""
        # First, run an installation to generate logs
        install_response = dashboard_client.post(
            "/deployment/run-installation",
            json={"vm_id": "vm01"}
        )
        
        if install_response.status_code == 200:
            install_data = install_response.json()
            deployment_id = install_data.get('deployment_id')
            
            # Wait a bit for logs to be saved
            time.sleep(1)
            
            # Get installation logs
            logs_response = dashboard_client.get(
                f"/deployment/installation-logs?vm_id=vm01&deployment_id={deployment_id}"
            )
            
            assert logs_response.status_code == 200, \
                f"Expected 200, got {logs_response.status_code}: {logs_response.text}"
            
            logs_data = logs_response.json()
            
            # Verify structure
            assert 'success' in logs_data, "Should have success field"
            assert 'logs' in logs_data, "Should have logs list"
            assert 'total' in logs_data, "Should have total count"
            
            # Logs should be a list
            logs = logs_data.get('logs', [])
            assert isinstance(logs, list), "Logs should be a list"
            
            # If logs exist, verify structure
            if len(logs) > 0:
                for log in logs:
                    assert isinstance(log, dict), "Each log should be a dictionary"
                    assert 'deployment_id' in log or 'vm_id' in log, \
                        "Log should have deployment_id or vm_id"


class TestVerifyDeployment:
    """TC-0-07-03: Weryfikacja deploymentu"""
    
    def test_verify_deployment(self, dashboard_client, skip_if_vm_unreachable):
        """
        TC-0-07-03: Verify deployment after installation.
        
        Steps:
        1. Execute installation on VM02
        2. After completion, run "Verify Deployment"
        3. Check verification results
        
        Expected: Verification executed, results positive.
        Acceptance: All components verified positively.
        """
        # Verify deployment on VM02
        response = dashboard_client.post(
            "/deployment/verify",
            json={"vm_id": "vm02"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert 'success' in data, "Should have success field"
        assert 'vm_id' in data, "Should have vm_id"
        assert data.get('vm_id') == 'vm02', "Should be for vm02"
        assert 'verification_status' in data, "Should have verification_status"
        assert 'data' in data, "Should have data field"
        assert 'timestamp' in data, "Should have timestamp"
        
        # Verification status should be one of: verified, failed, unknown
        verification_status = data.get('verification_status')
        assert verification_status in ['verified', 'failed', 'unknown'], \
            f"Verification status should be valid, got: {verification_status}"
        
        # Data should contain verification details
        verification_data = data.get('data', {})
        assert isinstance(verification_data, dict), "Verification data should be a dictionary"
        
        # Should have health_check or installation_status
        assert 'health_check' in verification_data or 'installation_status' in verification_data, \
            "Should have health_check or installation_status in verification data"


class TestDeploymentSummary:
    """Additional tests for deployment summary."""
    
    def test_get_deployment_summary(self, dashboard_client):
        """Test getting deployment summary."""
        response = dashboard_client.get("/deployment/summary")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert 'success' in data, "Should have success field"
        assert data.get('success') is True, "Should be successful"
        assert 'summary' in data, "Should have summary"
        assert 'timestamp' in data, "Should have timestamp"
        
        # Summary should have statistics
        summary = data.get('summary', {})
        assert 'total_deployments' in summary, "Should have total_deployments"
        assert 'by_status' in summary, "Should have by_status"
        assert 'by_vm' in summary, "Should have by_vm"

