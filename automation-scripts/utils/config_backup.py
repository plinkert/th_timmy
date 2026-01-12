"""
Configuration Backup - Backup and restore utilities for configurations.

This module provides utilities for backing up and restoring configuration files
with versioning, metadata tracking, and integrity verification.
"""

import os
import shutil
import hashlib
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import yaml


class ConfigBackupError(Exception):
    """Base exception for configuration backup errors."""
    pass


class ConfigBackup:
    """
    Configuration backup and restore manager.
    
    Provides functionality for:
    - Creating configuration backups
    - Restoring from backups
    - Listing and managing backups
    - Verifying backup integrity
    """
    
    def __init__(
        self,
        backup_dir: str = "configs/backups",
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Configuration Backup manager.
        
        Args:
            backup_dir: Directory for storing backups
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.debug(f"ConfigBackup initialized with backup_dir: {self.backup_dir}")
    
    def create_backup(
        self,
        config_path: str,
        backup_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create backup of configuration file.
        
        Args:
            config_path: Path to configuration file to backup
            backup_name: Custom backup name (auto-generated if None)
            metadata: Optional metadata to store with backup
        
        Returns:
            Dictionary with backup information
        
        Raises:
            ConfigBackupError: If backup fails
        """
        try:
            config_path = Path(config_path)
            
            if not config_path.exists():
                raise ConfigBackupError(f"Configuration file not found: {config_path}")
            
            # Generate backup name
            if not backup_name:
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                backup_name = f"{config_path.stem}_backup_{timestamp}{config_path.suffix}"
            
            backup_path = self.backup_dir / backup_name
            
            # Copy file
            shutil.copy2(config_path, backup_path)
            
            # Calculate file hash
            file_hash = self._calculate_file_hash(backup_path)
            
            # Create metadata
            backup_metadata = {
                'backup_name': backup_name,
                'backup_path': str(backup_path),
                'original_path': str(config_path),
                'file_hash': file_hash,
                'file_size': backup_path.stat().st_size,
                'timestamp': datetime.utcnow().isoformat(),
                'metadata': metadata or {}
            }
            
            # Save metadata
            metadata_path = self.backup_dir / f"{backup_name}.meta.json"
            with open(metadata_path, 'w') as f:
                json.dump(backup_metadata, f, indent=2)
            
            self.logger.info(f"Configuration backed up: {backup_path}")
            
            return {
                'success': True,
                'backup_name': backup_name,
                'backup_path': str(backup_path),
                'metadata': backup_metadata
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            raise ConfigBackupError(f"Backup creation failed: {e}")
    
    def restore_backup(
        self,
        backup_name: str,
        target_path: Optional[str] = None,
        verify: bool = True
    ) -> Dict[str, Any]:
        """
        Restore configuration from backup.
        
        Args:
            backup_name: Name of backup file
            target_path: Target path for restore (default: original path from metadata)
            verify: Whether to verify backup integrity before restore
        
        Returns:
            Dictionary with restore result
        
        Raises:
            ConfigBackupError: If restore fails
        """
        try:
            backup_path = self.backup_dir / backup_name
            
            if not backup_path.exists():
                raise ConfigBackupError(f"Backup not found: {backup_path}")
            
            # Load metadata
            metadata_path = self.backup_dir / f"{backup_name}.meta.json"
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                original_path = metadata.get('original_path')
            else:
                metadata = {}
                original_path = None
            
            # Determine target path
            if not target_path:
                if original_path:
                    target_path = original_path
                else:
                    raise ConfigBackupError(
                        "Target path not specified and not found in metadata"
                    )
            
            target_path = Path(target_path)
            
            # Verify backup integrity if requested
            if verify:
                current_hash = self._calculate_file_hash(backup_path)
                expected_hash = metadata.get('file_hash')
                
                if expected_hash and current_hash != expected_hash:
                    raise ConfigBackupError(
                        f"Backup integrity check failed. "
                        f"Expected hash: {expected_hash}, got: {current_hash}"
                    )
            
            # Create backup of current file if it exists
            if target_path.exists():
                current_backup_name = f"{target_path.stem}_before_restore_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}{target_path.suffix}"
                self.create_backup(str(target_path), current_backup_name)
            
            # Ensure target directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Restore file
            shutil.copy2(backup_path, target_path)
            
            # Verify restore
            restored_hash = self._calculate_file_hash(target_path)
            backup_hash = self._calculate_file_hash(backup_path)
            
            if restored_hash != backup_hash:
                raise ConfigBackupError("Restore verification failed: hash mismatch")
            
            self.logger.info(f"Configuration restored from backup: {backup_name} -> {target_path}")
            
            return {
                'success': True,
                'backup_name': backup_name,
                'target_path': str(target_path),
                'restored_hash': restored_hash,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except ConfigBackupError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to restore backup: {e}")
            raise ConfigBackupError(f"Restore failed: {e}")
    
    def list_backups(self, pattern: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all available backups.
        
        Args:
            pattern: Optional pattern to filter backups (e.g., "config_*")
        
        Returns:
            List of backup metadata dictionaries
        """
        try:
            backups = []
            
            # Find all metadata files
            for metadata_file in self.backup_dir.glob("*.meta.json"):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    # Apply pattern filter if provided
                    if pattern:
                        backup_name = metadata.get('backup_name', '')
                        if not self._match_pattern(backup_name, pattern):
                            continue
                    
                    # Check if backup file still exists
                    backup_path = Path(metadata.get('backup_path', ''))
                    if backup_path.exists():
                        metadata['exists'] = True
                    else:
                        metadata['exists'] = False
                    
                    backups.append(metadata)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to load metadata from {metadata_file}: {e}")
                    continue
            
            # Sort by timestamp (newest first)
            backups.sort(
                key=lambda x: x.get('timestamp', ''),
                reverse=True
            )
            
            return backups
            
        except Exception as e:
            self.logger.error(f"Failed to list backups: {e}")
            return []
    
    def delete_backup(self, backup_name: str) -> Dict[str, Any]:
        """
        Delete backup and its metadata.
        
        Args:
            backup_name: Name of backup to delete
        
        Returns:
            Dictionary with deletion result
        """
        try:
            backup_path = self.backup_dir / backup_name
            metadata_path = self.backup_dir / f"{backup_name}.meta.json"
            
            deleted_files = []
            
            if backup_path.exists():
                backup_path.unlink()
                deleted_files.append(str(backup_path))
            
            if metadata_path.exists():
                metadata_path.unlink()
                deleted_files.append(str(metadata_path))
            
            if not deleted_files:
                return {
                    'success': False,
                    'error': f"Backup not found: {backup_name}"
                }
            
            self.logger.info(f"Backup deleted: {backup_name}")
            
            return {
                'success': True,
                'backup_name': backup_name,
                'deleted_files': deleted_files,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to delete backup: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_backup(self, backup_name: str) -> Dict[str, Any]:
        """
        Verify backup integrity.
        
        Args:
            backup_name: Name of backup to verify
        
        Returns:
            Dictionary with verification result
        """
        try:
            backup_path = self.backup_dir / backup_name
            
            if not backup_path.exists():
                return {
                    'valid': False,
                    'error': f"Backup file not found: {backup_path}"
                }
            
            # Load metadata
            metadata_path = self.backup_dir / f"{backup_name}.meta.json"
            if not metadata_path.exists():
                return {
                    'valid': False,
                    'error': "Metadata file not found"
                }
            
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Calculate current hash
            current_hash = self._calculate_file_hash(backup_path)
            expected_hash = metadata.get('file_hash')
            
            # Verify hash
            if expected_hash and current_hash != expected_hash:
                return {
                    'valid': False,
                    'error': f"Hash mismatch. Expected: {expected_hash}, got: {current_hash}",
                    'current_hash': current_hash,
                    'expected_hash': expected_hash
                }
            
            # Verify file size
            current_size = backup_path.stat().st_size
            expected_size = metadata.get('file_size')
            
            if expected_size and current_size != expected_size:
                return {
                    'valid': False,
                    'error': f"Size mismatch. Expected: {expected_size}, got: {current_size}",
                    'current_size': current_size,
                    'expected_size': expected_size
                }
            
            return {
                'valid': True,
                'backup_name': backup_name,
                'file_hash': current_hash,
                'file_size': current_size,
                'timestamp': metadata.get('timestamp')
            }
            
        except Exception as e:
            self.logger.error(f"Failed to verify backup: {e}")
            return {
                'valid': False,
                'error': str(e)
            }
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA256 hash of file.
        
        Args:
            file_path: Path to file
        
        Returns:
            Hexadecimal hash string
        """
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _match_pattern(self, text: str, pattern: str) -> bool:
        """
        Simple pattern matching (supports * wildcard).
        
        Args:
            text: Text to match
            pattern: Pattern with * wildcards
        
        Returns:
            True if matches
        """
        import fnmatch
        return fnmatch.fnmatch(text, pattern)

