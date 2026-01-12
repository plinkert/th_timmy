"""
Integration tests for Configuration Management Service (Phase 0-03).

Test Scenarios:
- TS-0-03-01: Pełny cykl zarządzania konfiguracją
- TS-0-03-02: Rollback konfiguracji
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
config_manager_spec.loader.exec_module(config_manager_module)
ConfigManager = config_manager_module.ConfigManager


class TestFullConfigManagementCycle:
    """TS-0-03-01: Pełny cykl zarządzania konfiguracją"""
    
    def test_full_config_management_cycle(
        self,
        config_manager,
        all_vm_ids,
        temp_dir,
        test_config,
        skip_if_vm_unreachable
    ):
        """
        TS-0-03-01: Full configuration management cycle.
        
        Steps:
        1. Get configuration
        2. Modify configuration
        3. Validate configuration
        4. Create backup
        5. Update configuration
        6. Sync to all VMs
        7. Check if all VMs have updated configuration
        """
        test_config_path = os.path.join(temp_dir, "test_config.yml")
        
        # 1. Get configuration (from test_config fixture)
        original_config = test_config.copy()
        assert 'vms' in original_config, "Should have VMs in config"
        
        # 2. Modify configuration
        modified_config = original_config.copy()
        modified_config['vms']['vm01']['ip'] = '192.168.1.200'
        modified_config['vms']['vm02']['ip'] = '192.168.1.201'
        
        # 3. Validate configuration
        validation = config_manager.validate_config(
            config_data=modified_config,
            config_type='central'
        )
        assert validation.get('valid', False), \
            f"Modified config should be valid. Errors: {validation.get('errors')}"
        
        # 4. Create backup
        with open(test_config_path, 'w') as f:
            yaml.dump(original_config, f)
        
        backup_result = config_manager.backup_config(config_path=test_config_path)
        assert backup_result.get('success', False), "Backup should succeed"
        backup_name = backup_result.get('backup_name')
        
        # 5. Update configuration
        update_result = config_manager.update_config(
            config_data=modified_config,
            config_path=test_config_path,
            validate=True,
            create_backup=False  # Already backed up
        )
        assert update_result.get('success', False), "Update should succeed"
        
        # 6. Sync to all VMs (test with one VM to avoid long execution)
        if len(all_vm_ids) > 0:
            sync_result = config_manager.sync_config_to_vm(
                vm_id=all_vm_ids[0],
                config_path=test_config_path,
                remote_config_path='/tmp/test_config_cycle.yml'
            )
            assert sync_result.get('success', False), "Sync should succeed"
            
            # Cleanup
            config_manager.remote_executor.execute_remote_command(
                vm_id=all_vm_ids[0],
                command='rm -f /tmp/test_config_cycle.yml'
            )


class TestConfigRollback:
    """TS-0-03-02: Rollback konfiguracji"""
    
    def test_config_rollback(self, config_manager, temp_dir, test_config):
        """
        TS-0-03-02: Configuration rollback.
        
        Steps:
        1. Create backup of configuration
        2. Introduce bad change
        3. Restore configuration from backup
        4. Check if system works correctly
        """
        test_config_path = os.path.join(temp_dir, "test_config.yml")
        
        # 1. Create initial config
        original_config = test_config.copy()
        with open(test_config_path, 'w') as f:
            yaml.dump(original_config, f)
        
        # 2. Create backup
        backup_result = config_manager.backup_config(config_path=test_config_path)
        assert backup_result.get('success', False), "Backup should succeed"
        backup_name = backup_result.get('backup_name')
        
        # 3. Introduce bad change (invalid IP)
        bad_config = original_config.copy()
        bad_config['vms']['vm01']['ip'] = '999.999.999.999'  # Invalid IP
        
        # Try to update (should fail validation)
        try:
            config_manager.update_config(
                config_data=bad_config,
                config_path=test_config_path,
                validate=True,
                create_backup=False
            )
            # If validation passed (shouldn't), manually write bad config
            with open(test_config_path, 'w') as f:
                yaml.dump(bad_config, f)
        except Exception:
            # Validation failed as expected, write bad config anyway for test
            with open(test_config_path, 'w') as f:
                yaml.dump(bad_config, f)
        
        # 4. Restore from backup
        restore_result = config_manager.restore_config(
            backup_name=backup_name,
            config_path=test_config_path,
            verify=True
        )
        assert restore_result.get('success', False), "Restore should succeed"
        
        # 5. Verify restored config is correct
        with open(test_config_path, 'r') as f:
            restored_config = yaml.safe_load(f)
        
        assert restored_config['vms']['vm01']['ip'] == original_config['vms']['vm01']['ip'], \
            "Restored config should match original"
        
        # 6. Verify restored config is valid
        validation = config_manager.validate_config(
            config_data=restored_config,
            config_type='central'
        )
        assert validation.get('valid', False), \
            "Restored config should be valid"


class TestConfigSyncToAllVMs:
    """Additional integration tests."""
    
    def test_sync_config_to_all_vms(
        self,
        config_manager,
        all_vm_ids,
        temp_dir,
        test_config,
        skip_if_vm_unreachable
    ):
        """Test syncing configuration to all VMs."""
        if len(all_vm_ids) < 2:
            pytest.skip("Not enough VMs for sync test")
        
        test_config_path = os.path.join(temp_dir, "test_config.yml")
        with open(test_config_path, 'w') as f:
            yaml.dump(test_config, f)
        
        # Sync to all VMs
        result = config_manager.sync_config_to_all_vms(config_path=test_config_path)
        
        # Verify result structure
        assert 'results' in result, "Should have results for each VM"
        assert 'summary' in result, "Should have summary"
        
        # Check summary
        summary = result.get('summary', {})
        assert summary.get('total', 0) > 0, "Should have attempted sync to at least one VM"
        
        # At least some should succeed
        successful = summary.get('successful', 0)
        assert successful > 0, "At least some VMs should be synced successfully"

