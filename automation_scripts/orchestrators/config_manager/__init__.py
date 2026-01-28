"""
Configuration Management Service (Step 0.3).

Central management and sync of config files on all VMs with validation (JSON Schema),
encrypted backup, and rollback. Uses Step 0.1 (remote_executor) for file transfer.
"""

from .config_manager import (
    get_config,
    update_config,
    backup_config,
    restore_config,
    sync_config_to_vm,
    ConfigManagerError,
)
from .config_validator import validate_config, validate_all_required_fields
from .config_backup import create_backup, restore_backup, list_backups, BackupError

__all__ = [
    "get_config",
    "update_config",
    "backup_config",
    "restore_config",
    "sync_config_to_vm",
    "ConfigManagerError",
    "validate_config",
    "validate_all_required_fields",
    "create_backup",
    "restore_backup",
    "list_backups",
    "BackupError",
]
