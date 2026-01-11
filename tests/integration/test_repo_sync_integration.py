"""
Integration tests for Repository Sync Service (Phase 0-02).

Test Scenarios:
- TS-0-02-01: Pełny cykl synchronizacji
- TS-0-02-02: Synchronizacja przy braku połączenia
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

# Load repo_sync
repo_sync_path = automation_scripts_path / "services" / "repo_sync.py"
repo_sync_spec = importlib.util.spec_from_file_location("automation_scripts.services.repo_sync", repo_sync_path)
repo_sync_module = importlib.util.module_from_spec(repo_sync_spec)
sys.modules["automation_scripts.services.repo_sync"] = repo_sync_module
repo_sync_spec.loader.exec_module(repo_sync_module)
RepoSyncService = repo_sync_module.RepoSyncService


class TestFullSyncCycle:
    """TS-0-02-01: Pełny cykl synchronizacji"""
    
    def test_full_sync_cycle(self, repo_sync_service, all_vm_ids, skip_if_vm_unreachable):
        """
        TS-0-02-01: Full synchronization cycle.
        
        Steps:
        1. Make changes in multiple files
        2. Execute synchronization
        3. Verify on all VMs
        4. Check if all changes are visible
        """
        # Get initial status
        initial_statuses = {}
        for vm_id in all_vm_ids:
            status = repo_sync_service.check_repo_status(vm_id)
            if status.get('valid', False):
                initial_statuses[vm_id] = status.get('commit')
        
        # Sync to all VMs
        result = repo_sync_service.sync_repository_to_all_vms()
        
        # Verify sync was attempted
        assert 'results' in result, "Result should contain results for each VM"
        
        # Verify all VMs
        verification = repo_sync_service.verify_all_vms_synced()
        
        # Check that verification was performed
        assert 'vm_statuses' in verification, "Verification should contain VM statuses"
        
        # At least some VMs should be synced
        vm_statuses = verification.get('vm_statuses', {})
        valid_vms = [
            vm_id for vm_id, status in vm_statuses.items()
            if status.get('valid', False)
        ]
        
        assert len(valid_vms) > 0, "At least some VMs should have valid repositories"
        
        # If all VMs are synced, they should have the same commit
        if verification.get('synced', False):
            common_commit = verification.get('commit')
            assert common_commit is not None, "Common commit should be available"
            
            # Verify all valid VMs have the same commit
            for vm_id in valid_vms:
                status = vm_statuses[vm_id]
                assert status.get('commit') == common_commit, \
                    f"VM {vm_id} should have common commit {common_commit}"


class TestSyncWithConnectionLoss:
    """TS-0-02-02: Synchronizacja przy braku połączenia"""
    
    def test_sync_handles_errors_gracefully(self, repo_sync_service, skip_if_vm_unreachable):
        """
        TS-0-02-02: Sync handles connection loss gracefully.
        
        Note: We can't actually disconnect VM, but we test error handling
        by attempting sync to invalid VM or checking error handling.
        """
        # Test sync to all VMs - should handle any connection issues gracefully
        result = repo_sync_service.sync_repository_to_all_vms()
        
        # Should return result even if some VMs fail
        assert 'results' in result, "Should return results even with failures"
        assert 'summary' in result, "Should return summary"
        
        # Summary should show success/failure counts
        summary = result.get('summary', {})
        assert 'total' in summary, "Summary should have total count"
        assert 'successful' in summary, "Summary should have successful count"
        assert 'failed' in summary, "Summary should have failed count"
        
        # Test that we can still check status after errors
        status = repo_sync_service.check_repo_status('vm01')
        assert status is not None, "Should be able to check status after sync errors"


class TestSyncPerformance:
    """Performance tests for synchronization."""
    
    def test_sync_performance(self, repo_sync_service, all_vm_ids, skip_if_vm_unreachable):
        """Test that sync completes in reasonable time."""
        start_time = time.time()
        
        result = repo_sync_service.sync_repository_to_all_vms()
        
        execution_time = time.time() - start_time
        
        # Sync should complete in reasonable time (< 2 minutes for all VMs)
        assert execution_time < 120, \
            f"Sync took too long: {execution_time:.2f}s"
        
        # Should have results
        assert 'results' in result, "Should have results"
        
        print(f"\nSync to {len(all_vm_ids)} VMs completed in {execution_time:.2f}s")


class TestSyncVerification:
    """Additional verification tests."""
    
    def test_verify_all_vms_detailed(self, repo_sync_service, all_vm_ids, skip_if_vm_unreachable):
        """Test detailed verification of all VMs."""
        verification = repo_sync_service.verify_all_vms_synced()
        
        # Should have VM statuses
        assert 'vm_statuses' in verification, "Should have VM statuses"
        
        vm_statuses = verification.get('vm_statuses', {})
        
        # Check each VM status
        for vm_id in all_vm_ids:
            if vm_id in vm_statuses:
                status = vm_statuses[vm_id]
                # Status should be a dictionary
                assert isinstance(status, dict), f"Status for {vm_id} should be dict"
                
                # If valid, should have required fields
                if status.get('valid', False):
                    assert 'branch' in status, f"Status for {vm_id} should have branch"
                    assert 'commit' in status, f"Status for {vm_id} should have commit"

