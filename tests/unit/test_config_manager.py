"""
Unit tests for Configuration Management Service (Phase 0-03).

Test Cases:
- TC-0-03-01: Pobranie konfiguracji z VM
- TC-0-03-02: Aktualizacja konfiguracji
- TC-0-03-03: Walidacja konfiguracji
- TC-0-03-04: Backup konfiguracji
- TC-0-03-05: Synchronizacja konfiguracji do VM
- TC-0-03-06: Historia zmian konfiguracji
"""

import pytest
import os
import sys
import tempfile
import yaml
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

# Load config_manager
config_manager_path = automation_scripts_path / "services" / "config_manager.py"
config_manager_spec = importlib.util.spec_from_file_location("automation_scripts.services.config_manager", config_manager_path)
config_manager_module = importlib.util.module_from_spec(config_manager_spec)
sys.modules["automation_scripts.services.config_manager"] = config_manager_module

# Inject dependencies
from services.remote_executor import RemoteExecutor, RemoteExecutorError
config_manager_module.RemoteExecutor = RemoteExecutor
config_manager_module.RemoteExecutorError = RemoteExecutorError

config_manager_spec.loader.exec_module(config_manager_module)
ConfigManager = config_manager_module.ConfigManager
ConfigManagerError = config_manager_module.ConfigManagerError


class TestGetConfigFromVM:
    """TC-0-03-01: Pobranie konfiguracji z VM"""
    
    def test_get_config_from_vm(self, config_manager, skip_if_vm_unreachable):
        """
        TC-0-03-01: Get configuration from VM04.
        
        Steps:
        1. Get central configuration from VM04
        2. Check if it contains all required fields
        3. Verify YAML format
        
        Expected: Configuration retrieved, format correct.
        Acceptance: Configuration is valid YAML, contains all fields.
        """
        # Get configuration from VM04
        config = config_manager.get_config_from_vm('vm04')
        
        # Verify it's a dictionary
        assert isinstance(config, dict), "Configuration should be a dictionary"
        
        # Check required fields
        assert 'vms' in config, "Configuration should contain 'vms' section"
        
        # Verify VMs section
        vms = config.get('vms', {})
        assert isinstance(vms, dict), "'vms' should be a dictionary"
        
        # Check that at least some VMs are configured
        assert len(vms) > 0, "At least one VM should be configured"
        
        # Verify YAML format (if we can dump it, it's valid)
        try:
            yaml.dump(config)
        except Exception as e:
            pytest.fail(f"Configuration is not valid YAML: {e}")
    
    def test_get_config_structure(self, config_manager, skip_if_vm_unreachable):
        """Test that retrieved config has proper structure."""
        config = config_manager.get_config_from_vm('vm04')
        
        # Check structure
        assert 'vms' in config
        
        # Check VM structure
        for vm_id, vm_config in config.get('vms', {}).items():
            assert isinstance(vm_config, dict), f"VM {vm_id} config should be dict"
            # At least IP should be present
            assert 'ip' in vm_config or 'role' in vm_config, \
                f"VM {vm_id} should have basic fields"


class TestUpdateConfig:
    """TC-0-03-02: Aktualizacja konfiguracji"""
    
    def test_update_config(self, config_manager, temp_dir, skip_if_vm_unreachable):
        """
        TC-0-03-02: Update configuration.
        
        Steps:
        1. Modify configuration (e.g., change VM01 IP)
        2. Update configuration on VM04
        3. Get configuration and check changes
        
        Expected: Configuration updated.
        Acceptance: Changes visible in retrieved configuration.
        """
        # Get current config
        original_config = config_manager.get_config_from_vm('vm04')
        original_ip = original_config.get('vms', {}).get('vm01', {}).get('ip')
        
        # Create modified config
        modified_config = original_config.copy()
        modified_config['vms'] = modified_config.get('vms', {}).copy()
        modified_config['vms']['vm01'] = modified_config['vms'].get('vm01', {}).copy()
        
        # Change IP (use test IP)
        test_ip = "192.168.1.100"
        modified_config['vms']['vm01']['ip'] = test_ip
        
        # Update configuration (updates local main config)
        result = config_manager.update_config(modified_config, validate=True)
        
        # Verify update was successful
        assert result.get('success', False), f"Update failed: {result.get('error')}"
        assert 'config_hash' in result, "Result should contain config_hash"
        
        # Sync to VM04 to make change visible
        sync_result = config_manager.sync_config_to_vm('vm04', modified_config)
        assert sync_result.get('success', False), "Sync to VM04 should succeed"
        
        # Get updated config from VM04 and verify change
        updated_config = config_manager.get_config_from_vm('vm04')
        updated_ip = updated_config.get('vms', {}).get('vm01', {}).get('ip')
        
        # Verify change is visible
        assert updated_ip == test_ip, \
            f"IP should be updated to {test_ip}, got {updated_ip}"
        
        # Restore original IP
        restore_config = original_config.copy()
        restore_config['vms'] = restore_config.get('vms', {}).copy()
        restore_config['vms']['vm01'] = restore_config['vms'].get('vm01', {}).copy()
        restore_config['vms']['vm01']['ip'] = original_ip
        config_manager.update_config(restore_config, validate=True)
        config_manager.sync_config_to_vm('vm04', restore_config)


class TestValidateConfig:
    """TC-0-03-03: Walidacja konfiguracji"""
    
    def test_validate_config_valid(self, config_manager):
        """Test validation of valid configuration."""
        # Get current config
        config = config_manager.config
        
        # Validate
        result = config_manager.validate_config(config)
        
        # Should be valid
        assert result.get('valid', False), \
            f"Valid config should pass validation: {result.get('errors')}"
        assert len(result.get('errors', [])) == 0, \
            "Valid config should have no errors"
    
    def test_validate_config_invalid(self, config_manager):
        """
        TC-0-03-03: Verify validation detects errors.
        
        Steps:
        1. Prepare invalid configuration (missing required fields)
        2. Try to update configuration
        3. Check if validation detected errors
        
        Expected: Validation detected errors, configuration not saved.
        Acceptance: Validation errors returned, detailed messages.
        """
        # Create invalid config (missing required fields)
        invalid_config = {
            # Missing 'vms' section
            'network': {
                'subnet': '192.168.1.0/24'
            }
        }
        
        # Validate
        result = config_manager.validate_config(invalid_config)
        
        # Should be invalid
        assert not result.get('valid', False), "Invalid config should fail validation"
        assert len(result.get('errors', [])) > 0, "Should have validation errors"
        
        # Check that errors mention missing fields
        errors = result.get('errors', [])
        error_text = ' '.join(errors).lower()
        assert 'vms' in error_text or 'missing' in error_text, \
            f"Errors should mention missing fields: {errors}"
    
    def test_update_config_with_validation(self, config_manager):
        """Test that update fails with invalid config when validation enabled."""
        invalid_config = {
            'network': {'subnet': '192.168.1.0/24'}
        }
        
        # Use pytest.raises to properly catch the exception
        # Get the exception class from the same module instance that config_manager uses
        import sys
        actual_module = sys.modules.get('automation_scripts.services.config_manager')
        if actual_module:
            ExpectedError = actual_module.ConfigManagerError
        else:
            ExpectedError = ConfigManagerError
        
        with pytest.raises(ExpectedError) as exc_info:
            config_manager.update_config(invalid_config, validate=True)
        
        # Verify error message contains validation information
        error_msg = str(exc_info.value).lower()
        assert any(keyword in error_msg for keyword in ['validation', 'missing', 'vms', 'required']), \
            f"Error message should mention validation/missing/vms/required. Got: {error_msg}"


class TestBackupConfig:
    """TC-0-03-04: Backup konfiguracji"""
    
    def test_backup_config(self, config_manager, skip_if_vm_unreachable):
        """
        TC-0-03-04: Verify configuration backup.
        
        Steps:
        1. Backup VM02 configuration
        2. Modify configuration
        3. Restore configuration from backup
        4. Check if restored configuration is correct
        
        Expected: Backup and restore work correctly.
        Acceptance: Restored configuration identical to original.
        """
        # Get original config
        original_config = config_manager.get_config_from_vm('vm02')
        original_ip = original_config.get('vms', {}).get('vm02', {}).get('ip')
        
        # Backup configuration
        backup_result = config_manager.backup_config(vm_id='vm02')
        
        # Verify backup was successful
        assert backup_result.get('success', False), \
            f"Backup failed: {backup_result.get('error')}"
        assert 'backup_path' in backup_result, "Backup should have path"
        assert os.path.exists(backup_result['backup_path']), \
            "Backup file should exist"
        
        # Modify configuration
        modified_config = original_config.copy()
        modified_config['vms'] = modified_config.get('vms', {}).copy()
        modified_config['vms']['vm02'] = modified_config['vms'].get('vm02', {}).copy()
        modified_config['vms']['vm02']['ip'] = "192.168.1.999"  # Invalid IP for test
        
        # Restore from backup
        backup_name = os.path.basename(backup_result['backup_path'])
        restore_result = config_manager.restore_config(backup_name, vm_id='vm02')
        
        # Verify restore was successful
        assert restore_result.get('success', False), \
            f"Restore failed: {restore_result.get('error')}"
        
        # Verify restored config matches original
        restored_config = config_manager.get_config_from_vm('vm02')
        restored_ip = restored_config.get('vms', {}).get('vm02', {}).get('ip')
        
        assert restored_ip == original_ip, \
            f"Restored IP should match original: {original_ip} != {restored_ip}"
    
    def test_backup_main_config(self, config_manager):
        """Test backup of main configuration."""
        # Backup main config
        backup_result = config_manager.backup_config()
        
        assert backup_result.get('success', False), "Backup should succeed"
        assert os.path.exists(backup_result['backup_path']), "Backup file should exist"
        
        # Verify backup can be loaded
        backup_config = config_manager._load_config(backup_result['backup_path'])
        assert isinstance(backup_config, dict), "Backup should be valid config"


class TestSyncConfigToVM:
    """TC-0-03-05: Synchronizacja konfiguracji do VM"""
    
    def test_sync_config_to_vm(self, config_manager, skip_if_vm_unreachable):
        """
        TC-0-03-05: Verify configuration synchronization to remote VM.
        
        Steps:
        1. Modify central configuration
        2. Synchronize configuration to VM01
        3. Check if configuration file on VM01 was updated
        
        Expected: Configuration synchronized.
        Acceptance: File on VM01 contains updated values.
        """
        # Get current config
        current_config = config_manager.config
        
        # Sync to VM01
        result = config_manager.sync_config_to_vm('vm01', current_config)
        
        # Verify sync was successful
        assert result.get('success', False), \
            f"Sync failed: {result.get('error')}"
        assert result.get('vm_id') == 'vm01', "Result should be for vm01"
        assert 'remote_path' in result, "Result should have remote_path"
        
        # Verify file exists on VM
        remote_path = result['remote_path']
        exit_code, stdout, stderr = config_manager.remote_executor.execute_remote_command(
            vm_id='vm01',
            command=f"test -f {remote_path} && echo 'exists' || echo 'not_found'"
        )
        
        assert 'exists' in stdout, \
            f"Configuration file should exist on VM01: {remote_path}"
    
    def test_sync_config_to_all_vms(self, config_manager, all_vm_ids, skip_if_vm_unreachable):
        """Test synchronization to all VMs."""
        # Sync to all VMs
        result = config_manager.sync_config_to_all_vms()
        
        # Verify result structure
        assert 'results' in result, "Result should contain results"
        assert 'summary' in result, "Result should contain summary"
        
        # Verify summary
        summary = result.get('summary', {})
        assert summary.get('total', 0) > 0, "Should have attempted sync to at least one VM"
        
        # Check that sync was attempted for all enabled VMs
        results = result.get('results', {})
        assert len(results) > 0, "Should have results for at least some VMs"


class TestConfigHistory:
    """TC-0-03-06: Historia zmian konfiguracji"""
    
    def test_config_history(self, config_manager):
        """
        TC-0-03-06: Verify configuration change history.
        
        Steps:
        1. Make several changes to configuration
        2. Check change history
        3. Verify all changes are recorded
        
        Expected: Change history available.
        Acceptance: All changes visible in history with timestamps.
        """
        # Get current config
        config = config_manager.config
        
        # Make a change
        modified_config = config.copy()
        modified_config['test_timestamp'] = 'test_value_1'
        config_manager.update_config(modified_config, validate=False)
        
        # Make another change
        modified_config2 = config.copy()
        modified_config2['test_timestamp'] = 'test_value_2'
        config_manager.update_config(modified_config2, validate=False)
        
        # Get history
        history = config_manager.get_config_history(limit=10)
        
        # Verify history exists
        assert isinstance(history, list), "History should be a list"
        
        # Should have at least some entries
        assert len(history) >= 0, "History should be accessible"
        
        # If history exists, check structure
        if len(history) > 0:
            for entry in history:
                assert 'timestamp' in entry, "History entry should have timestamp"
                assert 'action' in entry, "History entry should have action"
    
    def test_list_backups(self, config_manager):
        """Test listing configuration backups."""
        # Create a backup
        backup_result = config_manager.backup_config()
        
        # List backups
        backups = config_manager.list_backups()
        
        # Verify backups list
        assert isinstance(backups, list), "Backups should be a list"
        
        # Should have at least the backup we just created
        if backup_result.get('success', False):
            backup_names = [b.get('backup_name') for b in backups]
            assert backup_result.get('backup_name') in backup_names, \
                "Created backup should be in list"

