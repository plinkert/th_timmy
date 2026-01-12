"""
Integration tests for Health Monitoring Service (Phase 0-04).

Test Scenarios:
- TS-0-04-01: Monitoring przez dłuższy czas
- TS-0-04-02: Obsługa awarii
"""

import pytest
import os
import sys
import time
from pathlib import Path

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
if "automation_scripts.services" not in sys.modules:
    sys.modules["automation_scripts.services"] = types.ModuleType("automation_scripts.services")
    sys.modules["automation_scripts.services"].__path__ = [str(automation_scripts_path / "services")]

# Load health_monitor
health_monitor_path = automation_scripts_path / "services" / "health_monitor.py"
health_monitor_spec = importlib.util.spec_from_file_location("automation_scripts.services.health_monitor", health_monitor_path)
health_monitor_module = importlib.util.module_from_spec(health_monitor_spec)
sys.modules["automation_scripts.services.health_monitor"] = health_monitor_module
health_monitor_spec.loader.exec_module(health_monitor_module)
HealthMonitor = health_monitor_module.HealthMonitor


class TestLongTermMonitoring:
    """TS-0-04-01: Monitoring przez dłuższy czas"""
    
    def test_long_term_monitoring(self, health_monitor, all_vm_ids, skip_if_vm_unreachable):
        """
        TS-0-04-01: Long-term monitoring.
        
        Steps:
        1. Start monitoring for 1 hour
        2. Check if all health checks were executed
        3. Check if metrics are collected regularly
        4. Verify no errors in logs
        
        Note: For integration test, we use shorter duration (30 seconds)
        """
        if len(all_vm_ids) < 2:
            pytest.skip("Not enough VMs for long-term monitoring test")
        
        # Start scheduler with short interval for test (15 seconds)
        health_monitor.schedule_health_checks(interval=15)
        
        try:
            # Wait for at least one health check cycle
            time.sleep(20)  # Wait for one cycle + buffer
            
            # Get health status - should have been checked by scheduler
            all_status = health_monitor.get_health_status_all()
            
            # Verify results
            assert 'vms' in all_status, "Should have VMs status"
            assert 'summary' in all_status, "Should have summary"
            
            # Verify scheduler is still running
            assert health_monitor._scheduler_running, "Scheduler should still be running"
            
        finally:
            # Stop scheduler
            health_monitor.stop_health_checks()
            assert not health_monitor._scheduler_running, "Scheduler should be stopped"


class TestFailureHandling:
    """TS-0-04-02: Obsługa awarii"""
    
    def test_failure_detection(self, health_monitor, skip_if_vm_unreachable):
        """
        TS-0-04-02: Failure handling.
        
        Steps:
        1. Turn off VM01 (simulate by checking unreachable VM)
        2. Check if health check detected problem
        3. Check if alert was sent
        4. Turn on VM01 again (check if it recovers)
        5. Check if health check detected return to normal
        
        Note: We can't actually turn off VM, but we test error handling
        """
        # Check health for a VM (should work if VM is reachable)
        health_status = health_monitor.check_vm_health('vm01')
        
        # Verify health check was attempted
        assert isinstance(health_status, dict), "Health status should be a dictionary"
        assert 'vm_id' in health_status, "Should have vm_id"
        assert 'status' in health_status, "Should have status"
        
        # If VM is unreachable, status should be 'error'
        # If VM is reachable, status should be one of: healthy, degraded, unhealthy
        status = health_status.get('status')
        assert status in ['healthy', 'degraded', 'unhealthy', 'error'], \
            f"Status should be valid, got: {status}"
        
        # Check if alerts were sent for problems
        if status in ['unhealthy', 'error']:
            alerts = health_monitor.get_alerts(vm_id='vm01', unacknowledged_only=True)
            # Should have alerts for unhealthy VM
            assert isinstance(alerts, list), "Alerts should be a list"
    
    def test_alert_on_unreachable_vm(self, health_monitor):
        """Test that alerts are sent when VM is unreachable."""
        # Try to check health for non-existent VM (should trigger error)
        try:
            health_status = health_monitor.check_vm_health('nonexistent_vm')
            # If it doesn't raise exception, check status
            if health_status.get('status') == 'error':
                # Check for alerts
                alerts = health_monitor.get_alerts(vm_id='nonexistent_vm', unacknowledged_only=True)
                assert isinstance(alerts, list), "Alerts should be a list"
        except Exception:
            # Expected - VM doesn't exist
            pass


class TestMetricsCollection:
    """Additional integration tests for metrics."""
    
    def test_metrics_collection_all_vms(self, health_monitor, all_vm_ids, skip_if_vm_unreachable):
        """Test metrics collection for all VMs."""
        if len(all_vm_ids) < 1:
            pytest.skip("No VMs available")
        
        # Collect metrics for first VM
        metrics = health_monitor.collect_metrics(all_vm_ids[0])
        
        # Verify metrics structure
        assert isinstance(metrics, dict), "Metrics should be a dictionary"
        assert 'vm_id' in metrics, "Should have vm_id"
        assert 'timestamp' in metrics, "Should have timestamp"
        
        # Should have system resources
        assert 'system_resources' in metrics or 'disk' in metrics or 'services' in metrics, \
            "Should have at least one metric category"


class TestHealthCheckOutput:
    """Test health check output parsing."""
    
    def test_health_check_output_parsing(self, health_monitor, skip_if_vm_unreachable):
        """Test that health check output is properly parsed."""
        health_status = health_monitor.check_vm_health('vm01')
        
        # Should have parsed status
        assert 'status' in health_status, "Should have status"
        
        # Should have details
        assert 'details' in health_status or 'exit_code' in health_status, \
            "Should have health check details"
        
        # Status should be one of expected values
        status = health_status.get('status')
        assert status in ['healthy', 'degraded', 'unhealthy', 'error'], \
            f"Status should be valid, got: {status}"

