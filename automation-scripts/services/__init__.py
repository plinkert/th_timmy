"""
Remote execution services for VM management.

This module provides services for remote command execution, file transfer,
script execution, repository synchronization, and configuration management
on virtual machines.
"""

from .remote_executor import RemoteExecutor
from .ssh_client import SSHClient
from .config_manager import ConfigManager

# Temporarily disable repo_sync import to avoid import errors in tests
# from .repo_sync import RepoSyncService

__all__ = ['RemoteExecutor', 'SSHClient', 'ConfigManager']  # 'RepoSyncService']

