"""
Integration tests for Management Dashboard API (Phase 0-05).

Test Scenarios:
- TS-0-05-01: Pełny cykl zarządzania z dashboardu
- TS-0-05-02: Wielu użytkowników jednocześnie
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


class TestFullManagementCycle:
    """TS-0-05-01: Pełny cykl zarządzania z dashboardu"""
    
    def test_full_management_cycle(self, dashboard_client, all_vm_ids, skip_if_vm_unreachable):
        """
        TS-0-05-01: Full management cycle from dashboard.
        
        Steps:
        1. Open dashboard
        2. Check status of all VMs
        3. Execute repository sync
        4. Edit configuration
        5. Run health check
        6. Check results
        """
        if len(all_vm_ids) < 1:
            pytest.skip("No VMs available for full cycle test")
        
        # 1. Get system overview (check status of all VMs)
        overview_response = dashboard_client.get("/system-overview")
        assert overview_response.status_code == 200
        overview_data = overview_response.json()
        assert 'vms' in overview_data, "Should have VMs in overview"
        assert 'summary' in overview_data, "Should have summary in overview"
        
        # 2. Execute repository sync
        sync_response = dashboard_client.post(
            "/sync-repository",
            json={}
        )
        assert sync_response.status_code == 200
        sync_data = sync_response.json()
        assert 'success' in sync_data, "Sync should have success field"
        
        # 3. Get and update configuration
        # Get current config
        get_config_response = dashboard_client.get("/config")
        assert get_config_response.status_code == 200
        current_config = get_config_response.json().get('config', {})
        
        # Update config (add test field)
        modified_config = current_config.copy()
        modified_config['test_cycle_timestamp'] = f'cycle_{int(time.time())}'
        
        update_config_response = dashboard_client.post(
            "/config",
            json={
                "config_data": modified_config,
                "validate": True,
                "create_backup": True
            }
        )
        assert update_config_response.status_code == 200
        update_data = update_config_response.json()
        assert update_data.get('success') is True, "Config update should succeed"
        
        # 4. Run health check
        health_check_response = dashboard_client.post(
            "/health-check",
            json={"vm_id": all_vm_ids[0]}
        )
        assert health_check_response.status_code == 200
        health_data = health_check_response.json()
        assert health_data.get('success') is True, "Health check should succeed"
        assert 'status' in health_data, "Should have status"
        
        # 5. Verify all operations completed
        # All responses should have been successful
        assert overview_response.status_code == 200
        assert sync_response.status_code == 200
        assert update_config_response.status_code == 200
        assert health_check_response.status_code == 200


class TestConcurrentUsers:
    """TS-0-05-02: Wielu użytkowników jednocześnie"""
    
    def test_concurrent_operations(self, dashboard_client, skip_if_vm_unreachable):
        """
        TS-0-05-02: Multiple users simultaneously.
        
        Steps:
        1. Open dashboard from 2 different browsers
        2. Execute different operations simultaneously
        3. Check if there are no conflicts
        4. Check if all operations executed correctly
        
        Note: For integration test, we simulate concurrent requests.
        """
        # Simulate concurrent requests
        import threading
        
        results = {}
        errors = []
        
        def get_overview():
            try:
                response = dashboard_client.get("/system-overview")
                results['overview'] = response.status_code
            except Exception as e:
                errors.append(f"Overview error: {e}")
                results['overview'] = None
        
        def get_config():
            try:
                response = dashboard_client.get("/config")
                results['config'] = response.status_code
            except Exception as e:
                errors.append(f"Config error: {e}")
                results['config'] = None
        
        def health_check():
            try:
                response = dashboard_client.post(
                    "/health-check",
                    json={"vm_id": "vm01"}
                )
                results['health_check'] = response.status_code
            except Exception as e:
                errors.append(f"Health check error: {e}")
                results['health_check'] = None
        
        # Run operations concurrently
        threads = [
            threading.Thread(target=get_overview),
            threading.Thread(target=get_config),
            threading.Thread(target=health_check)
        ]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join(timeout=30)
        
        # Verify all operations completed successfully
        assert len(errors) == 0, f"Should have no errors, got: {errors}"
        assert 'overview' in results, "Overview should have completed"
        assert 'config' in results, "Config should have completed"
        assert 'health_check' in results, "Health check should have completed"
        
        # All should return 200
        assert results.get('overview') == 200, "Overview should return 200"
        assert results.get('config') == 200, "Config should return 200"
        assert results.get('health_check') == 200, "Health check should return 200"


class TestDashboardEndpoints:
    """Additional integration tests for dashboard endpoints."""
    
    def test_health_endpoint(self, dashboard_client):
        """Test health endpoint."""
        response = dashboard_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') == 'healthy'
        assert data.get('service') == 'dashboard-api'
    
    def test_api_key_authentication(self, dashboard_client):
        """Test that API works without API key (development mode)."""
        # Should work without API key in development mode
        response = dashboard_client.get("/system-overview")
        assert response.status_code == 200, "Should work without API key in dev mode"

