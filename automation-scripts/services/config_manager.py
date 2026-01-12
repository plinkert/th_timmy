"""
Configuration Management Service - Central configuration management.

This module provides services for managing configuration files across all VMs,
including reading, updating, validating, backing up, and synchronizing configurations.
"""

import os
import logging
import shutil
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import yaml
import json

from .remote_executor import RemoteExecutor, RemoteExecutorError


class ConfigManagerError(Exception):
    """Base exception for configuration manager errors."""
    pass


class ConfigManager:
    """
    Configuration management service.
    
    Provides functionality for:
    - Reading configuration from VMs
    - Updating configuration
    - Validating configuration
    - Backing up and restoring configuration
    - Synchronizing configuration to VMs
    - Tracking configuration change history
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        remote_executor: Optional[RemoteExecutor] = None,
        backup_dir: Optional[str] = None,
        history_dir: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Configuration Manager.
        
        Args:
            config_path: Path to config.yml file
            config: Configuration dict (alternative to config_path)
            remote_executor: Optional RemoteExecutor instance
            backup_dir: Directory for configuration backups
            history_dir: Directory for configuration change history
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Load configuration
        if config:
            self.config = config
        elif config_path:
            self.config = self._load_config(config_path)
        else:
            # Try default config path
            default_config = Path(__file__).parent.parent.parent / "configs" / "config.yml"
            if default_config.exists():
                self.config = self._load_config(str(default_config))
            else:
                raise ConfigManagerError(
                    "No configuration provided. Specify config_path or config parameter."
                )
        
        # Get configuration management settings
        self.config_mgmt = self.config.get('configuration_management', {})
        
        # Initialize remote executor
        if remote_executor:
            self.remote_executor = remote_executor
        else:
            self.remote_executor = RemoteExecutor(
                config=self.config,
                logger=self.logger
            )
        
        # Setup directories
        self.backup_dir = Path(backup_dir or self.config_mgmt.get('backup_dir', 'configs/backups'))
        self.history_dir = Path(history_dir or self.config_mgmt.get('history_dir', 'configs/history'))
        
        # Create directories if they don't exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        
        # Main config path (on VM04 - orchestrator)
        self.main_config_path = self.config_mgmt.get(
            'main_config_path',
            str(Path(__file__).parent.parent.parent / "configs" / "config.yml")
        )
        
        # VM config paths
        self.vm_config_paths = self.config_mgmt.get('vm_config_paths', {})
        if not self.vm_config_paths:
            # Default paths
            default_path = '/home/thadmin/th_timmy/configs/config.yml'
            self.vm_config_paths = {
                'vm01': default_path,
                'vm02': default_path,
                'vm03': default_path,
                'vm04': default_path,
            }
        
        self.logger.info("ConfigManager initialized")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            self.logger.debug(f"Configuration loaded from {config_path}")
            return config
        except Exception as e:
            raise ConfigManagerError(f"Failed to load configuration from {config_path}: {e}")
    
    def _save_config(self, config: Dict[str, Any], config_path: str) -> None:
        """Save configuration to YAML file."""
        try:
            # Ensure directory exists
            Path(config_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            self.logger.debug(f"Configuration saved to {config_path}")
        except Exception as e:
            raise ConfigManagerError(f"Failed to save configuration to {config_path}: {e}")
    
    def _get_vm_config_path(self, vm_id: str) -> str:
        """Get configuration file path for VM."""
        return self.vm_config_paths.get(vm_id, f'/home/thadmin/th_timmy/configs/config.yml')
    
    def _validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate configuration structure.
        
        Args:
            config: Configuration dictionary
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required top-level keys
        required_keys = ['vms']
        for key in required_keys:
            if key not in config:
                errors.append(f"Missing required key: {key}")
        
        # Validate VMs section
        if 'vms' in config:
            vms = config['vms']
            if not isinstance(vms, dict):
                errors.append("'vms' must be a dictionary")
            else:
                # Check each VM has required fields
                for vm_id, vm_config in vms.items():
                    if not isinstance(vm_config, dict):
                        errors.append(f"VM '{vm_id}' configuration must be a dictionary")
                        continue
                    
                    if 'ip' not in vm_config:
                        errors.append(f"VM '{vm_id}' missing required field: 'ip'")
                    if 'role' not in vm_config:
                        errors.append(f"VM '{vm_id}' missing required field: 'role'")
        
        # Validate YAML structure (basic check)
        try:
            yaml.dump(config)
        except Exception as e:
            errors.append(f"Invalid YAML structure: {e}")
        
        return len(errors) == 0, errors
    
    def _calculate_config_hash(self, config: Dict[str, Any]) -> str:
        """Calculate hash of configuration for change tracking."""
        config_str = yaml.dump(config, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]
    
    def get_config_from_vm(self, vm_id: str = 'vm04') -> Dict[str, Any]:
        """
        Get configuration from VM.
        
        Args:
            vm_id: VM identifier (default: vm04 - orchestrator)
        
        Returns:
            Configuration dictionary
        
        Raises:
            ConfigManagerError: If configuration cannot be retrieved
        """
        try:
            config_path = self._get_vm_config_path(vm_id)
            
            self.logger.info(f"Retrieving configuration from {vm_id}: {config_path}")
            
            # Download config file to temporary location
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            try:
                self.remote_executor.download_file(
                    vm_id=vm_id,
                    remote_path=config_path,
                    local_path=tmp_path
                )
                
                # Load and return config
                config = self._load_config(tmp_path)
                return config
                
            finally:
                # Cleanup
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    
        except RemoteExecutorError as e:
            raise ConfigManagerError(f"Failed to retrieve configuration from {vm_id}: {e}")
        except Exception as e:
            raise ConfigManagerError(f"Unexpected error retrieving configuration from {vm_id}: {e}")
    
    def update_config(self, new_config: Dict[str, Any], validate: bool = True) -> Dict[str, Any]:
        """
        Update configuration.
        
        Args:
            new_config: New configuration dictionary
            validate: Whether to validate before saving
        
        Returns:
            Dictionary with update result
        
        Raises:
            ConfigManagerError: If validation fails
        """
        try:
            # Validate if requested
            if validate:
                is_valid, errors = self._validate_config(new_config)
                if not is_valid:
                    raise ConfigManagerError(
                        f"Configuration validation failed: {', '.join(errors)}"
                    )
            
            # Calculate hash for change tracking
            config_hash = self._calculate_config_hash(new_config)
            
            # Save to main config path
            self._save_config(new_config, self.main_config_path)
            
            # Record in history
            self._record_config_change(new_config, config_hash, 'update')
            
            self.logger.info(f"Configuration updated (hash: {config_hash})")
            
            return {
                'success': True,
                'config_hash': config_hash,
                'timestamp': datetime.utcnow().isoformat(),
                'message': 'Configuration updated successfully'
            }
            
        except ConfigManagerError:
            raise
        except Exception as e:
            raise ConfigManagerError(f"Failed to update configuration: {e}")
    
    def validate_config(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validate configuration.
        
        Args:
            config: Configuration to validate (default: current config)
        
        Returns:
            Dictionary with validation result
        """
        if config is None:
            config = self.config
        
        is_valid, errors = self._validate_config(config)
        
        return {
            'valid': is_valid,
            'errors': errors,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def backup_config(self, vm_id: Optional[str] = None, backup_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Backup configuration.
        
        Args:
            vm_id: VM identifier (None for main config)
            backup_name: Custom backup name (default: auto-generated)
        
        Returns:
            Dictionary with backup result
        """
        try:
            if vm_id:
                # Backup VM config
                config = self.get_config_from_vm(vm_id)
                source_path = self._get_vm_config_path(vm_id)
            else:
                # Backup main config
                config = self.config
                source_path = self.main_config_path
            
            # Generate backup name
            if not backup_name:
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                vm_suffix = f"_{vm_id}" if vm_id else ""
                backup_name = f"config_backup{vm_suffix}_{timestamp}.yml"
            
            backup_path = self.backup_dir / backup_name
            
            # Save backup
            self._save_config(config, str(backup_path))
            
            # Calculate hash
            config_hash = self._calculate_config_hash(config)
            
            # Record backup metadata
            backup_metadata = {
                'backup_name': backup_name,
                'backup_path': str(backup_path),
                'config_hash': config_hash,
                'vm_id': vm_id,
                'source_path': source_path,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            metadata_path = self.backup_dir / f"{backup_name}.meta.json"
            with open(metadata_path, 'w') as f:
                json.dump(backup_metadata, f, indent=2)
            
            self.logger.info(f"Configuration backed up: {backup_path}")
            
            return {
                'success': True,
                'backup_path': str(backup_path),
                'backup_name': backup_name,
                'config_hash': config_hash,
                'metadata': backup_metadata
            }
            
        except Exception as e:
            self.logger.error(f"Failed to backup configuration: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def restore_config(self, backup_name: str, vm_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Restore configuration from backup.
        
        Args:
            backup_name: Name of backup file
            vm_id: VM identifier (None for main config)
        
        Returns:
            Dictionary with restore result
        """
        try:
            backup_path = self.backup_dir / backup_name
            
            if not backup_path.exists():
                raise ConfigManagerError(f"Backup not found: {backup_path}")
            
            # Load backup
            config = self._load_config(str(backup_path))
            
            # Validate
            is_valid, errors = self._validate_config(config)
            if not is_valid:
                raise ConfigManagerError(f"Backup configuration is invalid: {', '.join(errors)}")
            
            # Restore
            if vm_id:
                # Restore to VM
                remote_path = self._get_vm_config_path(vm_id)
                self.remote_executor.upload_file(
                    vm_id=vm_id,
                    local_path=str(backup_path),
                    remote_path=remote_path
                )
            else:
                # Restore main config
                self._save_config(config, self.main_config_path)
                self.config = config
            
            # Record in history
            config_hash = self._calculate_config_hash(config)
            self._record_config_change(config, config_hash, 'restore', backup_name=backup_name)
            
            self.logger.info(f"Configuration restored from backup: {backup_name}")
            
            return {
                'success': True,
                'backup_name': backup_name,
                'config_hash': config_hash,
                'vm_id': vm_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to restore configuration: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def sync_config_to_vm(self, vm_id: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Synchronize configuration to VM.
        
        Args:
            vm_id: VM identifier
            config: Configuration to sync (default: current config)
        
        Returns:
            Dictionary with sync result
        """
        try:
            if config is None:
                config = self.config
            
            remote_path = self._get_vm_config_path(vm_id)
            
            # Save config to temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            try:
                # Save config to temp file
                self._save_config(config, tmp_path)
                
                # Upload to VM
                self.remote_executor.upload_file(
                    vm_id=vm_id,
                    local_path=tmp_path,
                    remote_path=remote_path
                )
                
                # Verify upload
                exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                    vm_id=vm_id,
                    command=f"test -f {remote_path} && echo 'exists' || echo 'not_found'"
                )
                
                if 'exists' not in stdout:
                    raise ConfigManagerError(f"Configuration file not found on {vm_id} after upload")
                
                self.logger.info(f"Configuration synchronized to {vm_id}: {remote_path}")
                
                return {
                    'success': True,
                    'vm_id': vm_id,
                    'remote_path': remote_path,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
            finally:
                # Cleanup
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    
        except Exception as e:
            self.logger.error(f"Failed to sync configuration to {vm_id}: {e}")
            return {
                'success': False,
                'vm_id': vm_id,
                'error': str(e)
            }
    
    def sync_config_to_all_vms(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Synchronize configuration to all enabled VMs.
        
        Args:
            config: Configuration to sync (default: current config)
        
        Returns:
            Dictionary with sync results
        """
        try:
            if config is None:
                config = self.config
            
            # Get all enabled VMs
            vms = self.config.get('vms', {})
            enabled_vms = [
                vm_id for vm_id, vm_config in vms.items()
                if vm_config.get('enabled', True)
            ]
            
            results = {}
            successful = 0
            failed = 0
            
            for vm_id in enabled_vms:
                result = self.sync_config_to_vm(vm_id, config)
                results[vm_id] = result
                
                if result.get('success', False):
                    successful += 1
                else:
                    failed += 1
            
            return {
                'success': failed == 0,
                'results': results,
                'summary': {
                    'total': len(enabled_vms),
                    'successful': successful,
                    'failed': failed
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to sync configuration to all VMs: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _record_config_change(
        self,
        config: Dict[str, Any],
        config_hash: str,
        action: str,
        backup_name: Optional[str] = None
    ) -> None:
        """
        Record configuration change in history.
        
        Args:
            config: Configuration dictionary
            config_hash: Configuration hash
            action: Action type (update, restore, etc.)
            backup_name: Backup name if restore
        """
        try:
            history_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'action': action,
                'config_hash': config_hash,
                'backup_name': backup_name
            }
            
            # Save history entry
            timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            history_file = self.history_dir / f"config_history_{timestamp_str}.json"
            
            with open(history_file, 'w') as f:
                json.dump(history_entry, f, indent=2)
            
            # Also append to main history log
            history_log = self.history_dir / "config_history.log"
            with open(history_log, 'a') as f:
                f.write(json.dumps(history_entry) + '\n')
                
        except Exception as e:
            self.logger.warning(f"Failed to record config change in history: {e}")
    
    def get_config_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get configuration change history.
        
        Args:
            limit: Maximum number of history entries to return
        
        Returns:
            List of history entries
        """
        try:
            history_log = self.history_dir / "config_history.log"
            
            if not history_log.exists():
                return []
            
            history_entries = []
            with open(history_log, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            entry = json.loads(line.strip())
                            history_entries.append(entry)
                        except json.JSONDecodeError:
                            continue
            
            # Return most recent entries
            return history_entries[-limit:]
            
        except Exception as e:
            self.logger.error(f"Failed to get config history: {e}")
            return []
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all configuration backups.
        
        Returns:
            List of backup metadata
        """
        try:
            backups = []
            
            for backup_file in self.backup_dir.glob("*.meta.json"):
                try:
                    with open(backup_file, 'r') as f:
                        metadata = json.load(f)
                    backups.append(metadata)
                except Exception:
                    continue
            
            # Sort by timestamp (newest first)
            backups.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return backups
            
        except Exception as e:
            self.logger.error(f"Failed to list backups: {e}")
            return []
    
    def close(self) -> None:
        """Close connections."""
        if self.remote_executor:
            self.remote_executor.close_connections()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.close()
        except Exception:
            pass

