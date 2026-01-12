"""
Configuration Management Service - Centralized configuration management.

This module provides services for managing configurations across all VMs,
including reading, updating, validating, backing up, and synchronizing configurations.
"""

import os
import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import yaml

from .remote_executor import RemoteExecutor, RemoteExecutorError

# Try relative imports first, fallback to absolute
try:
    from ..utils.config_validator import ConfigValidator, ConfigValidatorError
    from ..utils.config_backup import ConfigBackup, ConfigBackupError
except ImportError:
    # Fallback for direct execution or when package structure is different
    import sys
    from pathlib import Path
    automation_scripts_path = Path(__file__).parent.parent
    sys.path.insert(0, str(automation_scripts_path))
    from utils.config_validator import ConfigValidator, ConfigValidatorError
    from utils.config_backup import ConfigBackup, ConfigBackupError


class ConfigManagerError(Exception):
    """Base exception for configuration manager errors."""
    pass


class ConfigManager:
    """
    Configuration Management Service.
    
    Provides functionality for:
    - Reading configuration from VM
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
        history_file: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Configuration Manager.
        
        Args:
            config_path: Path to config.yml file
            config: Configuration dict (alternative to config_path)
            remote_executor: Optional RemoteExecutor instance
            backup_dir: Directory for configuration backups
            history_file: Path to configuration change history file
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
        
        # Get configuration paths
        self.config_paths = self.config.get('config_management', {}).get('paths', {})
        self.central_config_path = self.config_paths.get(
            'central',
            'configs/config.yml'
        )
        self.vm_config_paths = self.config_paths.get('vm', {})
        
        # Initialize remote executor
        if remote_executor:
            self.remote_executor = remote_executor
        else:
            self.remote_executor = RemoteExecutor(
                config=self.config,
                logger=self.logger
            )
        
        # Initialize validator
        self.validator = ConfigValidator(logger=self.logger)
        
        # Initialize backup manager
        backup_dir = backup_dir or self.config.get('config_management', {}).get(
            'backup_dir',
            'configs/backups'
        )
        self.backup_manager = ConfigBackup(backup_dir=backup_dir, logger=self.logger)
        
        # Initialize change history
        history_file = history_file or self.config.get('config_management', {}).get(
            'history_file',
            'configs/config_history.json'
        )
        self.history_file = Path(history_file)
        self._ensure_history_file()
        
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
    
    def _ensure_history_file(self) -> None:
        """Ensure history file exists."""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.history_file.exists():
            with open(self.history_file, 'w') as f:
                json.dump({'changes': []}, f, indent=2)
    
    def _add_to_history(
        self,
        operation: str,
        config_path: str,
        details: Dict[str, Any]
    ) -> None:
        """Add entry to configuration change history."""
        try:
            # Load existing history
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
            else:
                history = {'changes': []}
            
            # Add new entry
            entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'operation': operation,
                'config_path': config_path,
                'details': details
            }
            history['changes'].append(entry)
            
            # Keep only last 1000 entries
            if len(history['changes']) > 1000:
                history['changes'] = history['changes'][-1000:]
            
            # Save history
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            self.logger.warning(f"Failed to add entry to history: {e}")
    
    def get_config_from_vm(
        self,
        vm_id: str,
        config_type: str = "central"
    ) -> Dict[str, Any]:
        """
        Get configuration from VM.
        
        Args:
            vm_id: VM identifier
            config_type: Type of config ('central' or 'vm')
        
        Returns:
            Configuration dictionary
        
        Raises:
            ConfigManagerError: If retrieval fails
        """
        try:
            # Determine config path on VM
            if config_type == "central":
                config_path = self.central_config_path
            else:
                config_path = self.vm_config_paths.get(vm_id)
                if not config_path:
                    raise ConfigManagerError(f"No config path configured for {vm_id}")
            
            # Download config file to temporary location
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            try:
                # Download config from VM
                self.remote_executor.download_file(
                    vm_id=vm_id,
                    remote_path=config_path,
                    local_path=temp_path
                )
                
                # Load and return config
                with open(temp_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                return config
                
            finally:
                # Cleanup temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except RemoteExecutorError as e:
            raise ConfigManagerError(f"Failed to get config from {vm_id}: {e}")
        except Exception as e:
            raise ConfigManagerError(f"Unexpected error getting config from {vm_id}: {e}")
    
    def update_config(
        self,
        config_data: Dict[str, Any],
        config_path: Optional[str] = None,
        validate: bool = True,
        create_backup: bool = True
    ) -> Dict[str, Any]:
        """
        Update configuration file.
        
        Args:
            config_data: New configuration data
            config_path: Path to config file (default: central config path)
            validate: Whether to validate before saving
            create_backup: Whether to create backup before update
        
        Returns:
            Dictionary with update result
        
        Raises:
            ConfigManagerError: If update fails
        """
        try:
            if not config_path:
                config_path = self.central_config_path
            
            config_path = Path(config_path)
            
            # Validate configuration
            if validate:
                is_valid, errors = self.validator.validate_config(config_data, "central")
                if not is_valid:
                    raise ConfigManagerError(
                        f"Configuration validation failed: {', '.join(errors)}"
                    )
            
            # Create backup if requested
            backup_info = None
            if create_backup and config_path.exists():
                backup_info = self.backup_manager.create_backup(
                    str(config_path),
                    metadata={'operation': 'update', 'timestamp': datetime.utcnow().isoformat()}
                )
            
            # Ensure directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save configuration
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
            
            # Add to history
            self._add_to_history(
                operation='update',
                config_path=str(config_path),
                details={
                    'backup_created': backup_info is not None,
                    'backup_name': backup_info.get('backup_name') if backup_info else None
                }
            )
            
            self.logger.info(f"Configuration updated: {config_path}")
            
            return {
                'success': True,
                'config_path': str(config_path),
                'backup': backup_info,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except ConfigValidatorError as e:
            raise ConfigManagerError(f"Configuration validation error: {e}")
        except Exception as e:
            raise ConfigManagerError(f"Failed to update configuration: {e}")
    
    def validate_config(
        self,
        config_data: Optional[Dict[str, Any]] = None,
        config_path: Optional[str] = None,
        config_type: str = "central"
    ) -> Dict[str, Any]:
        """
        Validate configuration.
        
        Args:
            config_data: Configuration data to validate (if None, loads from config_path)
            config_path: Path to config file
            config_type: Type of configuration
        
        Returns:
            Dictionary with validation result
        """
        try:
            if config_data is None:
                if not config_path:
                    config_path = self.central_config_path
                is_valid, errors = self.validator.validate_config_file(
                    str(config_path),
                    config_type
                )
            else:
                is_valid, errors = self.validator.validate_config(config_data, config_type)
            
            return {
                'valid': is_valid,
                'errors': errors,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'valid': False,
                'errors': [str(e)],
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def backup_config(
        self,
        config_path: Optional[str] = None,
        backup_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create backup of configuration.
        
        Args:
            config_path: Path to config file (default: central config path)
            backup_name: Custom backup name
        
        Returns:
            Dictionary with backup information
        """
        try:
            if not config_path:
                config_path = self.central_config_path
            
            backup_info = self.backup_manager.create_backup(
                str(config_path),
                backup_name=backup_name,
                metadata={'operation': 'manual_backup', 'timestamp': datetime.utcnow().isoformat()}
            )
            
            # Add to history
            self._add_to_history(
                operation='backup',
                config_path=str(config_path),
                details={'backup_name': backup_info['backup_name']}
            )
            
            return backup_info
            
        except ConfigBackupError as e:
            raise ConfigManagerError(f"Backup failed: {e}")
    
    def restore_config(
        self,
        backup_name: str,
        config_path: Optional[str] = None,
        verify: bool = True
    ) -> Dict[str, Any]:
        """
        Restore configuration from backup.
        
        Args:
            backup_name: Name of backup to restore
            config_path: Target path (default: original path from backup)
            verify: Whether to verify backup integrity
        
        Returns:
            Dictionary with restore result
        """
        try:
            if not config_path:
                config_path = self.central_config_path
            
            restore_info = self.backup_manager.restore_backup(
                backup_name,
                target_path=str(config_path),
                verify=verify
            )
            
            # Add to history
            self._add_to_history(
                operation='restore',
                config_path=str(config_path),
                details={'backup_name': backup_name}
            )
            
            return restore_info
            
        except ConfigBackupError as e:
            raise ConfigManagerError(f"Restore failed: {e}")
    
    def sync_config_to_vm(
        self,
        vm_id: str,
        config_path: Optional[str] = None,
        remote_config_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synchronize configuration to remote VM.
        
        Args:
            vm_id: VM identifier
            config_path: Local config path (default: central config path)
            remote_config_path: Remote config path (default: same as local)
        
        Returns:
            Dictionary with sync result
        """
        try:
            if not config_path:
                config_path = self.central_config_path
            
            if not remote_config_path:
                remote_config_path = config_path
            
            # Validate before sync
            is_valid, errors = self.validator.validate_config_file(str(config_path), "central")
            if not is_valid:
                raise ConfigManagerError(
                    f"Configuration validation failed before sync: {', '.join(errors)}"
                )
            
            # Upload config to VM
            self.remote_executor.upload_file(
                vm_id=vm_id,
                local_path=str(config_path),
                remote_path=remote_config_path
            )
            
            # Add to history
            self._add_to_history(
                operation='sync_to_vm',
                config_path=str(config_path),
                details={'vm_id': vm_id, 'remote_path': remote_config_path}
            )
            
            self.logger.info(f"Configuration synced to {vm_id}: {remote_config_path}")
            
            return {
                'success': True,
                'vm_id': vm_id,
                'local_path': str(config_path),
                'remote_path': remote_config_path,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except RemoteExecutorError as e:
            raise ConfigManagerError(f"Failed to sync config to {vm_id}: {e}")
        except Exception as e:
            raise ConfigManagerError(f"Unexpected error syncing config to {vm_id}: {e}")
    
    def sync_config_to_all_vms(
        self,
        config_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synchronize configuration to all enabled VMs.
        
        Args:
            config_path: Local config path (default: central config path)
        
        Returns:
            Dictionary with sync results for all VMs
        """
        try:
            if not config_path:
                config_path = self.central_config_path
            
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
                try:
                    result = self.sync_config_to_vm(vm_id, config_path)
                    results[vm_id] = result
                    successful += 1
                except Exception as e:
                    results[vm_id] = {
                        'success': False,
                        'error': str(e)
                    }
                    failed += 1
            
            return {
                'success': failed == 0,
                'results': results,
                'summary': {
                    'total': len(enabled_vms),
                    'successful': successful,
                    'failed': failed
                }
            }
            
        except Exception as e:
            raise ConfigManagerError(f"Failed to sync config to all VMs: {e}")
    
    def get_config_history(
        self,
        limit: Optional[int] = None,
        operation: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get configuration change history.
        
        Args:
            limit: Maximum number of entries to return
            operation: Filter by operation type
        
        Returns:
            List of history entries
        """
        try:
            if not self.history_file.exists():
                return []
            
            with open(self.history_file, 'r') as f:
                history = json.load(f)
            
            changes = history.get('changes', [])
            
            # Filter by operation if specified
            if operation:
                changes = [c for c in changes if c.get('operation') == operation]
            
            # Apply limit
            if limit:
                changes = changes[-limit:]
            
            return changes
            
        except Exception as e:
            self.logger.error(f"Failed to get config history: {e}")
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

