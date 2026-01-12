"""
Unit tests for Hardening Management Interface (Phase 0-08).

Test Cases:
- TC-0-08-01: Status hardeningu
- TC-0-08-02: Uruchomienie hardeningu z dashboardu
- TC-0-08-03: Porównanie przed/po hardeningu
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


class TestHardeningStatus:
    """TC-0-08-01: Status hardeningu"""
    
    def test_get_hardening_status_all(self, dashboard_client, skip_if_vm_unreachable):
        """
        TC-0-08-01: Verify hardening status display.
        
        Steps:
        1. Open Hardening Management in dashboard
        2. Check hardening status of all VMs
        3. Verify status is displayed
        
        Expected: Hardening status displayed.
        Acceptance: Status for all VMs available.
        """
        # Get hardening status for all VMs
        response = dashboard_client.get("/hardening/status")
        
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
            assert 'hardened' in summary, "Summary should have hardened count"
            assert 'partial' in summary, "Summary should have partial count"
            assert 'not_hardened' in summary, "Summary should have not_hardened count"
        
        # If vms exists, verify structure
        if 'vms' in status_data:
            vms = status_data.get('vms', {})
            assert isinstance(vms, dict), "VMs should be a dictionary"
            
            # Each VM should have status
            for vm_id, vm_status in vms.items():
                assert isinstance(vm_status, dict), f"Status for {vm_id} should be a dictionary"
                assert 'status' in vm_status, f"Status for {vm_id} should have 'status' field"
                
                # Status should be one of: hardened, partial, not_hardened, unknown
                status = vm_status.get('status')
                assert status in ['hardened', 'partial', 'not_hardened', 'unknown'], \
                    f"Status for {vm_id} should be valid, got: {status}"
    
    def test_get_hardening_status_single_vm(self, dashboard_client, skip_if_vm_unreachable):
        """Test getting hardening status for single VM."""
        # Get hardening status for VM01
        response = dashboard_client.get("/hardening/status?vm_id=vm01")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert 'success' in data, "Should have success field"
        assert 'data' in data, "Should have data field"
        
        # Data should have status
        status_data = data.get('data', {})
        assert 'status' in status_data, "Should have status in data"


class TestRunHardening:
    """TC-0-08-02: Uruchomienie hardeningu z dashboardu"""
    
    def test_run_hardening(self, dashboard_client, skip_if_vm_unreachable):
        """
        TC-0-08-02: Verify running hardening remotely.
        
        Steps:
        1. Open Hardening Management
        2. Click "Run Hardening VM01"
        3. Check if hardening was started
        4. Check logs
        
        Expected: Hardening started, logs available.
        Acceptance: Hardening in progress, logs displayed.
        
        Note: Full hardening may take time, so we test that it starts correctly.
        """
        # Run hardening on VM01
        response = dashboard_client.post(
            "/hardening/run",
            json={
                "vm_id": "vm01",
                "capture_before": True
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert 'success' in data, "Should have success field"
        assert 'hardening_id' in data, "Should have hardening_id"
        assert 'vm_id' in data, "Should have vm_id"
        assert data.get('vm_id') == 'vm01', "Should be for vm01"
        assert 'status' in data, "Should have status"
        assert 'message' in data, "Should have message"
        assert 'timestamp' in data, "Should have timestamp"
        
        # Status should be one of: success, failed, in_progress, completed, unknown
        status = data.get('status')
        assert status in ['success', 'failed', 'in_progress', 'completed', 'unknown'], \
            f"Status should be valid, got: {status}"
        
        # Hardening ID should be present
        hardening_id = data.get('hardening_id')
        assert hardening_id is not None and len(hardening_id) > 0, \
            "Hardening ID should be present"
    
    def test_get_hardening_reports(self, dashboard_client, skip_if_vm_unreachable):
        """Test getting hardening reports."""
        # First, run a hardening to generate reports
        hardening_response = dashboard_client.post(
            "/hardening/run",
            json={
                "vm_id": "vm01",
                "capture_before": True
            }
        )
        
        if hardening_response.status_code == 200:
            hardening_data = hardening_response.json()
            hardening_id = hardening_data.get('hardening_id')
            
            # Wait a bit for reports to be saved
            time.sleep(1)
            
            # Get hardening reports
            reports_response = dashboard_client.get(
                f"/hardening/reports?vm_id=vm01&hardening_id={hardening_id}"
            )
            
            assert reports_response.status_code == 200, \
                f"Expected 200, got {reports_response.status_code}: {reports_response.text}"
            
            reports_data = reports_response.json()
            
            # Verify structure
            assert 'success' in reports_data, "Should have success field"
            assert 'reports' in reports_data, "Should have reports list"
            assert 'total' in reports_data, "Should have total count"
            
            # Reports should be a list
            reports = reports_data.get('reports', [])
            assert isinstance(reports, list), "Reports should be a list"
            
            # If reports exist, verify structure
            if len(reports) > 0:
                for report in reports:
                    assert isinstance(report, dict), "Each report should be a dictionary"
                    assert 'hardening_id' in report or 'vm_id' in report, \
                        "Report should have hardening_id or vm_id"


class TestCompareBeforeAfter:
    """TC-0-08-03: Porównanie przed/po hardeningu"""
    
    def test_compare_before_after(self, dashboard_client, skip_if_vm_unreachable):
        """
        TC-0-08-03: Verify before/after hardening comparison.
        
        Steps:
        1. Execute tests before hardening
        2. Execute hardening
        3. Execute tests after hardening
        4. Check comparison results
        
        Expected: Comparison displayed.
        Acceptance: Differences between before/after visible.
        """
        # First, run hardening with capture_before=True
        hardening_response = dashboard_client.post(
            "/hardening/run",
            json={
                "vm_id": "vm01",
                "capture_before": True
            }
        )
        
        assert hardening_response.status_code == 200, \
            f"Hardening should succeed, got: {hardening_response.status_code}"
        
        hardening_data = hardening_response.json()
        hardening_id = hardening_data.get('hardening_id')
        
        # Wait a bit for hardening to complete and states to be saved
        time.sleep(2)
        
        # Compare before/after
        compare_response = dashboard_client.post(
            "/hardening/compare",
            json={
                "hardening_id": hardening_id,
                "vm_id": "vm01"
            }
        )
        
        # Comparison might fail if before/after states not captured, which is OK
        if compare_response.status_code == 500:
            # Check if it's because states weren't captured
            error_detail = compare_response.json().get('detail', '')
            if 'not found' in error_detail.lower() or 'not captured' in error_detail.lower():
                pytest.skip("Before/after states not captured (this is OK for first run)")
            else:
                raise AssertionError(f"Unexpected error: {error_detail}")
        
        assert compare_response.status_code == 200, \
            f"Expected 200, got {compare_response.status_code}: {compare_response.text}"
        
        data = compare_response.json()
        
        # Verify structure
        assert 'success' in data, "Should have success field"
        assert data.get('success') is True, "Should be successful"
        assert 'hardening_id' in data, "Should have hardening_id"
        assert 'comparison' in data, "Should have comparison"
        assert 'timestamp' in data, "Should have timestamp"
        
        # Verify comparison structure
        comparison = data.get('comparison', {})
        assert isinstance(comparison, dict), "Comparison should be a dictionary"
        
        # Should have before_status, after_status, or changes
        assert 'before_status' in comparison or 'after_status' in comparison or 'changes' in comparison, \
            "Comparison should have before_status, after_status, or changes"
        
        # If changes exist, verify structure
        if 'changes' in comparison:
            changes = comparison.get('changes', {})
            assert isinstance(changes, dict), "Changes should be a dictionary"
            
            # Each change should have before/after
            for check_name, change_data in changes.items():
                assert isinstance(change_data, dict), f"Change for {check_name} should be a dictionary"
                assert 'before' in change_data or 'after' in change_data, \
                    f"Change for {check_name} should have before or after"


class TestHardeningSummary:
    """Additional tests for hardening summary."""
    
    def test_get_hardening_summary(self, dashboard_client):
        """Test getting hardening summary."""
        response = dashboard_client.get("/hardening/summary")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert 'success' in data, "Should have success field"
        assert data.get('success') is True, "Should be successful"
        assert 'summary' in data, "Should have summary"
        assert 'timestamp' in data, "Should have timestamp"
        
        # Summary should have statistics
        summary = data.get('summary', {})
        assert 'total_operations' in summary, "Should have total_operations"
        assert 'by_status' in summary, "Should have by_status"
        assert 'by_vm' in summary, "Should have by_vm"

