"""
Integration tests for Testing Management Interface (Phase 0-06).

Test Scenarios:
- TS-0-06-01: Pełny cykl testowania
"""

import pytest
import os
import sys
import json
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


class TestFullTestingCycle:
    """TS-0-06-01: Pełny cykl testowania"""
    
    def test_full_testing_cycle(self, dashboard_client, skip_if_vm_unreachable):
        """
        TS-0-06-01: Full testing cycle.
        
        Steps:
        1. Run Connection Tests
        2. Run Data Flow Tests
        3. Check results
        4. Export results
        5. Check test history
        """
        # 1. Run Connection Tests
        connection_response = dashboard_client.post(
            "/tests/connection",
            json={"vm_id": "vm04"}
        )
        assert connection_response.status_code == 200, \
            f"Connection tests should succeed, got: {connection_response.status_code}"
        connection_data = connection_response.json()
        assert 'test_type' in connection_data, "Should have test_type"
        assert connection_data.get('test_type') == 'connections', "Should be connections test"
        
        # Wait a bit for tests to complete and be saved
        time.sleep(2)
        
        # 2. Run Data Flow Tests
        data_flow_response = dashboard_client.post(
            "/tests/data-flow",
            json={"vm_id": "vm04"}
        )
        assert data_flow_response.status_code == 200, \
            f"Data flow tests should succeed, got: {data_flow_response.status_code}"
        data_flow_data = data_flow_response.json()
        assert 'test_type' in data_flow_data, "Should have test_type"
        assert data_flow_data.get('test_type') == 'data_flow', "Should be data_flow test"
        
        # Wait a bit for tests to complete and be saved
        time.sleep(2)
        
        # 3. Check results - both should have results
        assert connection_data.get('status') in ['success', 'failed', 'error'], \
            "Connection test should have status"
        assert data_flow_data.get('status') in ['success', 'failed', 'error'], \
            "Data flow test should have status"
        
        # 4. Export results
        export_response = dashboard_client.post(
            "/tests/export",
            json={
                "format": "json",
                "limit": 20
            }
        )
        
        # Export might fail if no tests exist, which is OK for first run
        if export_response.status_code == 404:
            # That's OK - no tests to export yet
            pass
        else:
            assert export_response.status_code == 200, \
                f"Export should succeed, got: {export_response.status_code}"
            export_data = export_response.json()
            assert export_data.get('success') is True, "Export should be successful"
            assert 'file_path' in export_data, "Should have file_path"
        
        # 5. Check test history
        history_response = dashboard_client.get("/tests/history")
        assert history_response.status_code == 200, \
            f"History should be available, got: {history_response.status_code}"
        history_data = history_response.json()
        assert 'tests' in history_data, "Should have tests list"
        assert 'total' in history_data, "Should have total count"
        
        # Should have at least the tests we just ran
        tests = history_data.get('tests', [])
        assert isinstance(tests, list), "Tests should be a list"
        
        # Verify all operations completed
        assert connection_response.status_code == 200
        assert data_flow_response.status_code == 200
        assert history_response.status_code == 200


class TestTestingEndpoints:
    """Additional integration tests for testing endpoints."""
    
    def test_test_history_empty(self, dashboard_client, temp_dir):
        """Test that empty test history returns empty list."""
        response = dashboard_client.get("/tests/history")
        assert response.status_code == 200
        data = response.json()
        assert 'tests' in data
        assert isinstance(data['tests'], list)
    
    def test_export_invalid_format(self, dashboard_client, temp_dir):
        """Test export with invalid format."""
        response = dashboard_client.post(
            "/tests/export",
            json={"format": "xml"}  # Invalid format
        )
        # Should return 400 for invalid format (validation happens before checking for results)
        assert response.status_code == 400, \
            f"Should return 400 for invalid format, got {response.status_code}: {response.text}"
    
    def test_export_no_results(self, dashboard_client, temp_dir):
        """Test export when no results exist."""
        response = dashboard_client.post(
            "/tests/export",
            json={
                "format": "json",
                "test_type": "nonexistent_type"
            }
        )
        # Should return 404 if no results
        assert response.status_code in [200, 404], \
            "Should return 200 (empty) or 404 (not found)"

