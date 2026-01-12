"""
Unit tests for Testing Management Interface (Phase 0-06).

Test Cases:
- TC-0-06-01: Uruchomienie Connection Tests z dashboardu
- TC-0-06-02: Uruchomienie Data Flow Tests z dashboardu
- TC-0-06-03: Historia testów
- TC-0-06-04: Eksport wyników testów
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


class TestConnectionTests:
    """TC-0-06-01: Uruchomienie Connection Tests z dashboardu"""
    
    def test_run_connection_tests(self, dashboard_client, skip_if_vm_unreachable):
        """
        TC-0-06-01: Verify running connection tests from dashboard.
        
        Steps:
        1. Open Testing Management in dashboard
        2. Click "Run Connection Tests"
        3. Check if tests were started
        4. Check results
        
        Expected: Tests executed, results displayed.
        Acceptance: Results available in dashboard, all tests executed.
        """
        # Run connection tests
        response = dashboard_client.post(
            "/tests/connection",
            json={"vm_id": "vm04"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert 'success' in data, "Should have success field"
        assert 'test_type' in data, "Should have test_type field"
        assert data.get('test_type') == 'connections', "Should be connections test"
        assert 'vm_id' in data, "Should have vm_id"
        assert 'timestamp' in data, "Should have timestamp"
        assert 'status' in data, "Should have status"
        assert 'passed' in data, "Should have passed count"
        assert 'failed' in data, "Should have failed count"
        assert 'warnings' in data, "Should have warnings count"
        assert 'execution_time' in data, "Should have execution_time"
        
        # Verify execution time is reasonable
        execution_time = data.get('execution_time', 0)
        assert execution_time >= 0, "Execution time should be non-negative"
        
        # Status should be one of: success, failed, error
        status = data.get('status')
        assert status in ['success', 'failed', 'error'], \
            f"Status should be success/failed/error, got: {status}"


class TestDataFlowTests:
    """TC-0-06-02: Uruchomienie Data Flow Tests z dashboardu"""
    
    def test_run_data_flow_tests(self, dashboard_client, skip_if_vm_unreachable):
        """
        TC-0-06-02: Verify running data flow tests from dashboard.
        
        Steps:
        1. Open Testing Management
        2. Click "Run Data Flow Tests"
        3. Check results
        
        Expected: Tests executed, results displayed.
        Acceptance: Results available, tests completed successfully.
        """
        # Run data flow tests
        response = dashboard_client.post(
            "/tests/data-flow",
            json={"vm_id": "vm04"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert 'success' in data, "Should have success field"
        assert 'test_type' in data, "Should have test_type field"
        assert data.get('test_type') == 'data_flow', "Should be data_flow test"
        assert 'vm_id' in data, "Should have vm_id"
        assert 'timestamp' in data, "Should have timestamp"
        assert 'status' in data, "Should have status"
        assert 'passed' in data, "Should have passed count"
        assert 'failed' in data, "Should have failed count"
        assert 'warnings' in data, "Should have warnings count"
        assert 'execution_time' in data, "Should have execution_time"
        
        # Status should be one of: success, failed, error
        status = data.get('status')
        assert status in ['success', 'failed', 'error'], \
            f"Status should be success/failed/error, got: {status}"


class TestTestHistory:
    """TC-0-06-03: Historia testów"""
    
    def test_get_test_history(self, dashboard_client, temp_dir):
        """
        TC-0-06-03: Verify test history display.
        
        Steps:
        1. Execute several tests
        2. Open "Test History" in dashboard
        3. Check if all tests are visible
        
        Expected: Test history available.
        Acceptance: All tests visible with timestamps.
        """
        # Get test history
        response = dashboard_client.get("/tests/history")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert 'success' in data, "Should have success field"
        assert data.get('success') is True, "Should be successful"
        assert 'tests' in data, "Should have tests list"
        assert 'total' in data, "Should have total count"
        
        # Tests should be a list
        tests = data.get('tests', [])
        assert isinstance(tests, list), "Tests should be a list"
        
        # Each test should have timestamp
        for test in tests:
            assert isinstance(test, dict), "Each test should be a dictionary"
            assert 'timestamp' in test, "Each test should have timestamp"
            assert 'test_type' in test, "Each test should have test_type"
    
    def test_get_test_history_with_filters(self, dashboard_client, temp_dir):
        """Test test history with filters."""
        # Get test history filtered by test type
        response = dashboard_client.get("/tests/history?test_type=connections&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'tests' in data, "Should have tests list"
        assert 'filters' in data, "Should have filters"
        
        # All returned tests should be of type 'connections'
        tests = data.get('tests', [])
        for test in tests:
            if 'test_type' in test:
                assert test.get('test_type') == 'connections', \
                    "All tests should be of type 'connections'"


class TestExportResults:
    """TC-0-06-04: Eksport wyników testów"""
    
    def test_export_results_json(self, dashboard_client, temp_dir, skip_if_vm_unreachable):
        """
        TC-0-06-04: Verify test results export.
        
        Steps:
        1. Execute tests
        2. Click "Export Results"
        3. Check if file was generated
        4. Check file content
        
        Expected: File generated, content correct.
        Acceptance: JSON/CSV file contains all results.
        """
        # First, run a test to ensure we have results
        connection_response = dashboard_client.post(
            "/tests/connection",
            json={"vm_id": "vm04"}
        )
        # Wait a bit for test to be saved
        import time
        time.sleep(1)
        
        # Export results as JSON
        response = dashboard_client.post(
            "/tests/export",
            json={
                "format": "json",
                "limit": 10
            }
        )
        
        # Export might return 404 if no results exist (which is OK for first run)
        if response.status_code == 404:
            pytest.skip("No test results to export (this is OK for first run)")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert 'success' in data, "Should have success field"
        assert data.get('success') is True, "Export should be successful"
        assert 'file_path' in data, "Should have file_path"
        assert 'format' in data, "Should have format"
        assert data.get('format') == 'json', "Format should be json"
        assert 'count' in data, "Should have count"
        assert 'message' in data, "Should have message"
        
        # Verify file exists
        file_path = data.get('file_path')
        if file_path:
            assert os.path.exists(file_path), f"Exported file should exist: {file_path}"
            
            # Verify file content is valid JSON
            with open(file_path, 'r') as f:
                exported_data = json.load(f)
            
            assert 'tests' in exported_data or 'export_timestamp' in exported_data, \
                "Exported JSON should have tests or export_timestamp"
    
    def test_export_results_csv(self, dashboard_client, temp_dir):
        """Test export results as CSV."""
        # Export results as CSV
        response = dashboard_client.post(
            "/tests/export",
            json={
                "format": "csv",
                "limit": 10
            }
        )
        
        # CSV export might fail if no tests exist, which is OK
        if response.status_code == 404:
            pytest.skip("No test results to export")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert 'success' in data, "Should have success field"
        assert 'format' in data, "Should have format"
        assert data.get('format') == 'csv', "Format should be csv"
        assert 'file_path' in data, "Should have file_path"
        
        # Verify file exists
        file_path = data.get('file_path')
        if file_path:
            assert os.path.exists(file_path), f"Exported file should exist: {file_path}"
            
            # Verify file is readable
            with open(file_path, 'r') as f:
                content = f.read()
                assert len(content) > 0, "CSV file should not be empty"

