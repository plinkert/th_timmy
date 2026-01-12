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
from ..utils.config_validator import ConfigValidator
from ..utils.config_backup import ConfigBackup


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
        
        # Initialize validator and backup manager
        self.validator = ConfigValidator(logger=self.logger)
        self.backup_manager = ConfigBackup(backup_dir=str(self.backup_dir), logger=self.logger)
        
        # Main config path (on VM04 - orchestrator)
        project_root = Path(__file__).parent.parent.parent
        self.main_config_path = self.config_mgmt.get(
            'main_config_path',
            str(project_root / "configs" / "config.yml")
        )
        
        # VM config paths - central config
        self.vm_config_paths = self.config_mgmt.get('vm_config_paths', {})
        if not self.vm_config_paths:
            # Default paths
            default_path = '/home/user/th_timmy/configs/config.yml'
            self.vm_config_paths = {
                'vm01': default_path,
                'vm02': default_path,
                'vm03': default_path,
                'vm04': default_path,
            }
        
        # VM-specific config paths (hosts/vmXX-*/config.yml)
        self.vm_specific_config_paths = self.config_mgmt.get('vm_specific_config_paths', {})
        if not self.vm_specific_config_paths:
            base_path = '/home/user/th_timmy/hosts'
            self.vm_specific_config_paths = {
                'vm01': f'{base_path}/vm01-ingest/config.yml',
                'vm02': f'{base_path}/vm02-database/config.yml',
                'vm03': f'{base_path}/vm03-analysis/config.yml',
                'vm04': f'{base_path}/vm04-orchestrator/config.yml',
            }
        
        # Environment file paths
        self.env_file_paths = self.config_mgmt.get('env_file_paths', {})
        if not self.env_file_paths:
            base_path = '/home/user/th_timmy'
            self.env_file_paths = {
                'vm01': f'{base_path}/.env',
                'vm02': f'{base_path}/.env',
                'vm03': f'{base_path}/.env',
                'vm04': f'{base_path}/.env',
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
    
    def _get_vm_config_path(self, vm_id: str, config_type: str = "central") -> str:
        """
        Get configuration file path for VM.
        
        Args:
            vm_id: VM identifier
            config_type: Type of configuration ('central', 'vm', 'env')
        
        Returns:
            Configuration file path
        """
        if config_type == "central":
            return self.vm_config_paths.get(vm_id, f'/home/user/th_timmy/configs/config.yml')
        elif config_type == "vm":
            return self.vm_specific_config_paths.get(
                vm_id,
                f'/home/user/th_timmy/hosts/vm{vm_id[-1]}-*/config.yml'
            )
        elif config_type == "env":
            return self.env_file_paths.get(vm_id, f'/home/user/th_timmy/.env')
        else:
            raise ConfigManagerError(f"Unknown config type: {config_type}")
    
    def _validate_config(
        self,
        config: Dict[str, Any],
        config_type: str = "central"
    ) -> Tuple[bool, List[str]]:
        """
        Validate configuration structure.
        
        Args:
            config: Configuration dictionary
            config_type: Type of configuration ('central', 'vm', 'env')
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        return self.validator.validate_config(config, config_type)
    
    def _calculate_config_hash(self, config: Dict[str, Any]) -> str:
        """Calculate hash of configuration for change tracking."""
        config_str = yaml.dump(config, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]
    
    def get_config(
        self,
        vm_id: str,
        config_type: str = "central"
    ) -> Dict[str, Any]:
        """
        Get configuration from VM.
        
        Args:
            vm_id: VM identifier
            config_type: Type of configuration ('central', 'vm', 'env')
        
        Returns:
            Configuration dictionary or string (for env files)
        
        Raises:
            ConfigManagerError: If configuration cannot be retrieved
        """
        try:
            config_path = self._get_vm_config_path(vm_id, config_type)
            
            self.logger.info(f"Retrieving {config_type} configuration from {vm_id}: {config_path}")
            
            # Download config file to temporary location
            import tempfile
            suffix = '.env' if config_type == 'env' else '.yml'
            with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            try:
                self.remote_executor.download_file(
                    vm_id=vm_id,
                    remote_path=config_path,
                    local_path=tmp_path
                )
                
                # Load and return config
                if config_type == 'env':
                    # Read as text for env files
                    with open(tmp_path, 'r') as f:
                        return f.read()
                else:
                    # Read as YAML
                    return self._load_config(tmp_path)
                
            finally:
                # Cleanup
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    
        except RemoteExecutorError as e:
            raise ConfigManagerError(f"Failed to retrieve configuration from {vm_id}: {e}")
        except Exception as e:
            raise ConfigManagerError(f"Unexpected error retrieving configuration from {vm_id}: {e}")
    
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
    
    def update_config(
        self,
        vm_id: Optional[str],
        config_type: str,
        config_data: Any,
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Update configuration.
        
        Args:
            vm_id: VM identifier (None for main/local config)
            config_type: Type of configuration ('central', 'vm', 'env')
            config_data: Configuration data (dict for YAML, str for env)
            validate: Whether to validate before saving
        
        Returns:
            Dictionary with update result
        
        Raises:
            ConfigManagerError: If validation fails
        """
        try:
            # Validate if requested
            if validate:
                if config_type == 'env':
                    is_valid, errors = self.validator.validate_config(config_data, 'env')
                else:
                    is_valid, errors = self.validator.validate_config(config_data, config_type)
                
                if not is_valid:
                    raise ConfigManagerError(
                        f"Configuration validation failed: {', '.join(errors)}"
                    )
            
            # Determine target path
            if vm_id:
                target_path = self._get_vm_config_path(vm_id, config_type)
            else:
                # Local update
                project_root = Path(__file__).parent.parent.parent
                if config_type == 'central':
                    target_path = str(project_root / "configs" / "config.yml")
                elif config_type == 'vm':
                    raise ConfigManagerError("VM-specific config requires vm_id")
                elif config_type == 'env':
                    target_path = str(project_root / ".env")
                else:
                    raise ConfigManagerError(f"Unknown config type: {config_type}")
            
            # Calculate hash for change tracking
            if config_type == 'env':
                config_hash = hashlib.sha256(str(config_data).encode()).hexdigest()[:16]
            else:
                config_hash = self._calculate_config_hash(config_data)
            
            if vm_id:
                # Save to temporary file and upload to VM
                import tempfile
                suffix = '.env' if config_type == 'env' else '.yml'
                with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                
                try:
                    if config_type == 'env':
                        # Write env file
                        with open(tmp_path, 'w') as f:
                            f.write(config_data if isinstance(config_data, str) else str(config_data))
                    else:
                        # Write YAML
                        self._save_config(config_data, tmp_path)
                    
                    # Upload to VM
                    self.remote_executor.upload_file(
                        vm_id=vm_id,
                        local_path=tmp_path,
                        remote_path=target_path
                    )
                    
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
            else:
                # Local save
                if config_type == 'env':
                    with open(target_path, 'w') as f:
                        f.write(config_data if isinstance(config_data, str) else str(config_data))
                else:
                    self._save_config(config_data, target_path)
                
                # Update local config if central
                if config_type == 'central':
                    self.config = config_data
            
            # Record in history
            if config_type != 'env':
                self._record_config_change(config_data, config_hash, 'update')
            
            self.logger.info(f"Configuration updated (type: {config_type}, hash: {config_hash})")
            
            return {
                'success': True,
                'config_hash': config_hash,
                'config_type': config_type,
                'vm_id': vm_id,
                'timestamp': datetime.utcnow().isoformat(),
                'message': 'Configuration updated successfully'
            }
            
        except ConfigManagerError:
            raise
        except Exception as e:
            raise ConfigManagerError(f"Failed to update configuration: {e}")
    
    def validate_config(
        self,
        config_data: Optional[Any] = None,
        config_type: str = "central"
    ) -> Dict[str, Any]:
        """
        Validate configuration.
        
        Args:
            config_data: Configuration to validate (default: current config)
            config_type: Type of configuration ('central', 'vm', 'env')
        
        Returns:
            Dictionary with validation result
        """
        if config_data is None:
            if config_type == 'central':
                config_data = self.config
            else:
                return {
                    'valid': False,
                    'errors': ['No configuration data provided'],
                    'timestamp': datetime.utcnow().isoformat()
                }
        
        is_valid, errors = self.validator.validate_config(config_data, config_type)
        
        return {
            'valid': is_valid,
            'errors': errors,
            'config_type': config_type,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def backup_config(
        self,
        vm_id: Optional[str] = None,
        config_type: str = "central",
        backup_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Backup configuration.
        
        Args:
            vm_id: VM identifier (None for main/local config)
            config_type: Type of configuration ('central', 'vm', 'env')
            backup_name: Custom backup name (default: auto-generated)
        
        Returns:
            Dictionary with backup result
        """
        try:
            if vm_id:
                # Backup VM config - download first
                config_data = self.get_config(vm_id, config_type)
                source_path = self._get_vm_config_path(vm_id, config_type)
                
                # Save to temporary file for backup
                import tempfile
                suffix = '.env' if config_type == 'env' else '.yml'
                with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                
                try:
                    if config_type == 'env':
                        with open(tmp_path, 'w') as f:
                            f.write(config_data if isinstance(config_data, str) else str(config_data))
                    else:
                        self._save_config(config_data, tmp_path)
                    
                    # Use backup manager
                    result = self.backup_manager.create_backup(
                        tmp_path,
                        backup_name,
                        metadata={
                            'vm_id': vm_id,
                            'config_type': config_type,
                            'source_path': source_path
                        }
                    )
                    
                    return result
                    
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
            else:
                # Backup local config
                project_root = Path(__file__).parent.parent.parent
                if config_type == 'central':
                    source_path = str(project_root / "configs" / "config.yml")
                elif config_type == 'env':
                    source_path = str(project_root / ".env")
                else:
                    raise ConfigManagerError(f"Cannot backup {config_type} config locally without vm_id")
                
                if not os.path.exists(source_path):
                    raise ConfigManagerError(f"Configuration file not found: {source_path}")
                
                # Use backup manager
                return self.backup_manager.create_backup(
                    source_path,
                    backup_name,
                    metadata={
                        'config_type': config_type,
                        'source_path': source_path
                    }
                )
            
        except Exception as e:
            self.logger.error(f"Failed to backup configuration: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def restore_config(
        self,
        backup_id: str,
        vm_id: Optional[str] = None,
        config_type: str = "central"
    ) -> Dict[str, Any]:
        """
        Restore configuration from backup.
        
        Args:
            backup_id: Backup name or ID
            vm_id: VM identifier (None for main/local config)
            config_type: Type of configuration ('central', 'vm', 'env')
        
        Returns:
            Dictionary with restore result
        """
        try:
            # Determine target path
            if vm_id:
                target_path = self._get_vm_config_path(vm_id, config_type)
            else:
                project_root = Path(__file__).parent.parent.parent
                if config_type == 'central':
                    target_path = str(project_root / "configs" / "config.yml")
                elif config_type == 'env':
                    target_path = str(project_root / ".env")
                else:
                    raise ConfigManagerError(f"Cannot restore {config_type} config locally without vm_id")
            
            # Use backup manager to restore
            result = self.backup_manager.restore_backup(backup_id, target_path, verify=True)
            
            if result.get('success'):
                # If restoring to VM, upload the restored file
                if vm_id:
                    # File was restored locally, now upload to VM
                    self.remote_executor.upload_file(
                        vm_id=vm_id,
                        local_path=target_path,
                        remote_path=self._get_vm_config_path(vm_id, config_type)
                    )
                elif config_type == 'central':
                    # Reload local config
                    self.config = self._load_config(target_path)
            
            self.logger.info(f"Configuration restored from backup: {backup_id}")
            
            return {
                'success': True,
                'backup_id': backup_id,
                'vm_id': vm_id,
                'config_type': config_type,
                'target_path': target_path,
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

