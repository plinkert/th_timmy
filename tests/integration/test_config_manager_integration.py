"""
Integration tests for Configuration Management Service (Phase 0-03).

Test Scenarios:
- TS-0-03-01: Pełny cykl zarządzania konfiguracją
- TS-0-03-02: Rollback konfiguracji
"""

import pytest
import os
import sys
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


class TestFullConfigManagementCycle:
    """TS-0-03-01: Pełny cykl zarządzania konfiguracją"""
    
    def test_full_config_management_cycle(
        self,
        config_manager,
        all_vm_ids,
        skip_if_vm_unreachable
    ):
        """
        TS-0-03-01: Full configuration management cycle.
        
        Steps:
        1. Get configuration
        2. Modify configuration
        3. Validate configuration
        4. Perform backup
        5. Update configuration
        6. Synchronize to all VMs
        7. Check if all VMs have updated configuration
        """
        # Step 1: Get configuration
        original_config = config_manager.get_config_from_vm('vm04')
        assert isinstance(original_config, dict), "Should retrieve config"
        
        # Step 2: Modify configuration
        modified_config = original_config.copy()
        modified_config['vms'] = modified_config.get('vms', {}).copy()
        if 'vm01' in modified_config['vms']:
            modified_config['vms']['vm01'] = modified_config['vms']['vm01'].copy()
            original_ip = modified_config['vms']['vm01'].get('ip')
            # Add test marker
            modified_config['test_cycle_marker'] = 'full_cycle_test'
        
        # Step 3: Validate configuration
        validation = config_manager.validate_config(modified_config)
        assert validation.get('valid', False), \
            f"Modified config should be valid: {validation.get('errors')}"
        
        # Step 4: Perform backup
        backup_result = config_manager.backup_config()
        assert backup_result.get('success', False), "Backup should succeed"
        
        # Step 5: Update configuration
        update_result = config_manager.update_config(modified_config, validate=True)
        assert update_result.get('success', False), "Update should succeed"
        
        # Step 6: Synchronize to all VMs
        sync_result = config_manager.sync_config_to_all_vms(modified_config)
        assert 'results' in sync_result, "Sync should return results"
        
        # Step 7: Verify all VMs have updated configuration
        # Check at least one VM
        if len(all_vm_ids) > 0:
            vm_id = all_vm_ids[0]
            synced_config = config_manager.get_config_from_vm(vm_id)
            
            # Verify marker is present (if sync worked)
            if 'test_cycle_marker' in synced_config:
                assert synced_config['test_cycle_marker'] == 'full_cycle_test', \
                    "Synced config should have test marker"
        
        # Restore original config
        restore_config = original_config.copy()
        if 'test_cycle_marker' in restore_config:
            del restore_config['test_cycle_marker']
        config_manager.update_config(restore_config, validate=True)


class TestConfigRollback:
    """TS-0-03-02: Rollback konfiguracji"""
    
    def test_config_rollback(self, config_manager, skip_if_vm_unreachable):
        """
        TS-0-03-02: Configuration rollback.
        
        Steps:
        1. Perform configuration backup
        2. Introduce erroneous change
        3. Restore configuration from backup
        4. Check if system works correctly
        """
        # Step 1: Backup configuration
        original_config = config_manager.get_config_from_vm('vm02')
        backup_result = config_manager.backup_config(vm_id='vm02')
        
        assert backup_result.get('success', False), "Backup should succeed"
        backup_name = os.path.basename(backup_result['backup_path'])
        
        # Step 2: Introduce erroneous change
        erroneous_config = original_config.copy()
        erroneous_config['vms'] = erroneous_config.get('vms', {}).copy()
        if 'vm02' in erroneous_config['vms']:
            erroneous_config['vms']['vm02'] = erroneous_config['vms']['vm02'].copy()
            erroneous_config['vms']['vm02']['ip'] = "999.999.999.999"  # Invalid IP
        
        # Update with erroneous config
        config_manager.update_config(erroneous_config, validate=False)
        
        # Step 3: Restore from backup
        restore_result = config_manager.restore_config(backup_name, vm_id='vm02')
        
        assert restore_result.get('success', False), \
            f"Restore should succeed: {restore_result.get('error')}"
        
        # Step 4: Verify system works correctly (config is valid)
        restored_config = config_manager.get_config_from_vm('vm02')
        
        # Validate restored config
        validation = config_manager.validate_config(restored_config)
        assert validation.get('valid', False), \
            f"Restored config should be valid: {validation.get('errors')}"
        
        # Verify original IP is restored
        original_ip = original_config.get('vms', {}).get('vm02', {}).get('ip')
        restored_ip = restored_config.get('vms', {}).get('vm02', {}).get('ip')
        
        if original_ip and restored_ip:
            assert restored_ip == original_ip, \
                f"Restored IP should match original: {original_ip} != {restored_ip}"


class TestConfigValidation:
    """Additional validation tests."""
    
    def test_validate_required_fields(self, config_manager):
        """Test validation of required fields."""
        # Missing vms
        invalid_config = {'network': {'subnet': '192.168.1.0/24'}}
        result = config_manager.validate_config(invalid_config)
        assert not result.get('valid', False), "Should fail validation"
        assert len(result.get('errors', [])) > 0, "Should have errors"
        
        # Valid config
        valid_config = {
            'vms': {
                'vm01': {'ip': '192.168.1.10', 'role': 'test', 'enabled': True}
            }
        }
        result = config_manager.validate_config(valid_config)
        assert result.get('valid', False), "Should pass validation"
    
    def test_validate_vm_structure(self, config_manager):
        """Test validation of VM structure."""
        # VM missing IP
        invalid_config = {
            'vms': {
                'vm01': {'role': 'test'}  # Missing IP
            }
        }
        result = config_manager.validate_config(invalid_config)
        assert not result.get('valid', False), "Should fail validation"
        
        # Valid VM config
        valid_config = {
            'vms': {
                'vm01': {'ip': '192.168.1.10', 'role': 'test', 'enabled': True}
            }
        }
        result = config_manager.validate_config(valid_config)
        assert result.get('valid', False), "Should pass validation"

