"""
Remote Execution Service - Main service for remote VM management.

This module provides high-level interface for executing commands, scripts,
and file operations on remote VMs with comprehensive logging and error handling.
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import yaml

from .ssh_client import SSHClient, SSHClientError


class RemoteExecutorError(Exception):
    """Base exception for remote executor errors."""
    pass


class RemoteExecutor:
    """
    Remote execution service for VM management.
    
    Provides high-level interface for:
    - Remote command execution
    - Remote script execution
    - File upload/download
    - Comprehensive audit logging
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        ssh_key_path: Optional[str] = None,
        ssh_password: Optional[str] = None,
        audit_log_path: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Remote Executor.
        
        Args:
            config_path: Path to config.yml file
            config: Configuration dict (alternative to config_path)
            ssh_key_path: Path to SSH private key (overrides config)
            ssh_password: SSH password (fallback, less secure)
            audit_log_path: Path to audit log file
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
                raise RemoteExecutorError(
                    "No configuration provided. Specify config_path or config parameter."
                )
        
        # SSH authentication
        self.ssh_key_path = ssh_key_path or os.getenv('SSH_KEY_PATH')
        self.ssh_password = ssh_password or os.getenv('SSH_PASSWORD')
        
        # Audit logging
        self.audit_log_path = audit_log_path or os.getenv(
            'AUDIT_LOG_PATH',
            'logs/remote_executor_audit.log'
        )
        self._ensure_audit_log_dir()
        
        # Cache for SSH clients (connection reuse)
        self._ssh_clients: Dict[str, SSHClient] = {}
        
        self.logger.info("RemoteExecutor initialized")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            self.logger.debug(f"Configuration loaded from {config_path}")
            return config
        except Exception as e:
            raise RemoteExecutorError(f"Failed to load configuration from {config_path}: {e}")
    
    def _ensure_audit_log_dir(self) -> None:
        """Ensure audit log directory exists."""
        log_dir = Path(self.audit_log_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_vm_config(self, vm_id: str) -> Dict[str, Any]:
        """
        Get VM configuration by ID.
        
        Args:
            vm_id: VM identifier (e.g., 'vm01', 'vm02')
        
        Returns:
            VM configuration dict
        
        Raises:
            RemoteExecutorError: If VM not found or disabled
        """
        vms = self.config.get('vms', {})
        
        if vm_id not in vms:
            raise RemoteExecutorError(f"VM '{vm_id}' not found in configuration")
        
        vm_config = vms[vm_id]
        
        if not vm_config.get('enabled', True):
            raise RemoteExecutorError(f"VM '{vm_id}' is disabled in configuration")
        
        return vm_config
    
    def _get_ssh_client(self, vm_id: str) -> SSHClient:
        """
        Get or create SSH client for VM.
        
        Args:
            vm_id: VM identifier
        
        Returns:
            SSHClient instance
        """
        # Return cached client if exists and connected
        if vm_id in self._ssh_clients:
            client = self._ssh_clients[vm_id]
            if client._connected:
                return client
        
        # Get VM configuration
        vm_config = self._get_vm_config(vm_id)
        
        # Determine SSH key path
        key_path = self.ssh_key_path
        if not key_path:
            # Try default SSH key locations
            default_keys = [
                Path.home() / '.ssh' / 'id_rsa',
                Path.home() / '.ssh' / 'id_ed25519',
                Path.home() / '.ssh' / 'id_rsa_th',
            ]
            for key in default_keys:
                if key.exists():
                    key_path = str(key)
                    break
        
        # Create SSH client
        client = SSHClient(
            hostname=vm_config['ip'],
            username=vm_config.get('ssh_user', 'thadmin'),
            port=vm_config.get('ssh_port', 22),
            key_path=key_path,
            password=self.ssh_password,
            timeout=self.config.get('hardening', {}).get('ssh', {}).get('timeout', 300),
            logger=self.logger
        )
        
        # Cache client
        self._ssh_clients[vm_id] = client
        
        return client
    
    def _audit_log(
        self,
        operation: str,
        vm_id: str,
        details: Dict[str, Any],
        status: str = "SUCCESS",
        error: Optional[str] = None
    ) -> None:
        """
        Write audit log entry.
        
        Args:
            operation: Operation name (e.g., 'execute_command')
            vm_id: VM identifier
            details: Operation details
            status: Operation status (SUCCESS, FAILED)
            error: Error message if failed
        """
        try:
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'operation': operation,
                'vm_id': vm_id,
                'status': status,
                'details': details,
            }
            
            if error:
                log_entry['error'] = error
            
            # Write to audit log file
            with open(self.audit_log_path, 'a') as f:
                import json
                f.write(json.dumps(log_entry) + '\n')
            
            # Also log to standard logger
            if status == "SUCCESS":
                self.logger.info(f"AUDIT: {operation} on {vm_id} - {status}")
            else:
                self.logger.error(f"AUDIT: {operation} on {vm_id} - {status}: {error}")
                
        except Exception as e:
            self.logger.warning(f"Failed to write audit log: {e}")
    
    def execute_remote_command(
        self,
        vm_id: str,
        command: str,
        user: Optional[str] = None,
        timeout: Optional[int] = None,
        environment: Optional[Dict[str, str]] = None
    ) -> Tuple[int, str, str]:
        """
        Execute command on remote VM.
        
        Args:
            vm_id: VM identifier (e.g., 'vm01')
            command: Command to execute
            user: Optional user to execute as (via sudo)
            timeout: Command timeout in seconds
            environment: Optional environment variables
        
        Returns:
            Tuple of (exit_code, stdout, stderr)
        
        Raises:
            RemoteExecutorError: If execution fails
        """
        try:
            # Get SSH client
            client = self._get_ssh_client(vm_id)
            
            # Prepare command with user if specified
            if user:
                command = f"sudo -u {user} {command}"
            
            # Connect if not connected
            if not client._connected:
                client.connect()
            
            # Execute command
            exit_code, stdout, stderr = client.execute_command(
                command,
                timeout=timeout,
                environment=environment
            )
            
            # Audit log
            self._audit_log(
                operation='execute_remote_command',
                vm_id=vm_id,
                details={
                    'command': command[:200],  # Truncate for logging
                    'exit_code': exit_code,
                    'stdout_length': len(stdout),
                    'stderr_length': len(stderr),
                    'user': user,
                    'timeout': timeout,
                },
                status='SUCCESS' if exit_code == 0 else 'FAILED'
            )
            
            return exit_code, stdout, stderr
            
        except SSHClientError as e:
            self._audit_log(
                operation='execute_remote_command',
                vm_id=vm_id,
                details={'command': command[:200]},
                status='FAILED',
                error=str(e)
            )
            raise RemoteExecutorError(f"Failed to execute command on {vm_id}: {e}")
        except Exception as e:
            self._audit_log(
                operation='execute_remote_command',
                vm_id=vm_id,
                details={'command': command[:200]},
                status='FAILED',
                error=str(e)
            )
            raise RemoteExecutorError(f"Unexpected error executing command on {vm_id}: {e}")
    
    def execute_remote_script(
        self,
        vm_id: str,
        script_path: str,
        args: Optional[List[str]] = None,
        user: Optional[str] = None,
        timeout: Optional[int] = None,
        interpreter: str = "/bin/bash"
    ) -> Tuple[int, str, str]:
        """
        Execute script on remote VM.
        
        Args:
            vm_id: VM identifier
            script_path: Path to script on remote VM
            args: Optional script arguments
            user: Optional user to execute as
            timeout: Script timeout in seconds
            interpreter: Script interpreter (default: /bin/bash)
        
        Returns:
            Tuple of (exit_code, stdout, stderr)
        
        Raises:
            RemoteExecutorError: If execution fails
        """
        try:
            # Prepare command
            script_cmd = f"{interpreter} {script_path}"
            if args:
                script_cmd += " " + " ".join(args)
            
            # Execute via execute_remote_command
            return self.execute_remote_command(
                vm_id=vm_id,
                command=script_cmd,
                user=user,
                timeout=timeout
            )
            
        except RemoteExecutorError:
            raise
        except Exception as e:
            raise RemoteExecutorError(f"Failed to execute script on {vm_id}: {e}")
    
    def upload_file(
        self,
        vm_id: str,
        local_path: str,
        remote_path: str,
        preserve_permissions: bool = False
    ) -> None:
        """
        Upload file to remote VM.
        
        Args:
            vm_id: VM identifier
            local_path: Local file path
            remote_path: Remote file path
            preserve_permissions: Whether to preserve file permissions
        
        Raises:
            RemoteExecutorError: If upload fails
        """
        try:
            # Validate local file
            if not os.path.exists(local_path):
                raise RemoteExecutorError(f"Local file not found: {local_path}")
            
            # Get SSH client
            client = self._get_ssh_client(vm_id)
            
            # Connect if not connected
            if not client._connected:
                client.connect()
            
            # Upload file
            client.upload_file(local_path, remote_path, preserve_permissions)
            
            # Audit log
            self._audit_log(
                operation='upload_file',
                vm_id=vm_id,
                details={
                    'local_path': local_path,
                    'remote_path': remote_path,
                    'file_size': os.path.getsize(local_path),
                    'preserve_permissions': preserve_permissions,
                },
                status='SUCCESS'
            )
            
        except SSHClientError as e:
            self._audit_log(
                operation='upload_file',
                vm_id=vm_id,
                details={'local_path': local_path, 'remote_path': remote_path},
                status='FAILED',
                error=str(e)
            )
            raise RemoteExecutorError(f"Failed to upload file to {vm_id}: {e}")
        except Exception as e:
            self._audit_log(
                operation='upload_file',
                vm_id=vm_id,
                details={'local_path': local_path, 'remote_path': remote_path},
                status='FAILED',
                error=str(e)
            )
            raise RemoteExecutorError(f"Unexpected error uploading file to {vm_id}: {e}")
    
    def download_file(
        self,
        vm_id: str,
        remote_path: str,
        local_path: str,
        preserve_permissions: bool = False
    ) -> None:
        """
        Download file from remote VM.
        
        Args:
            vm_id: VM identifier
            remote_path: Remote file path
            local_path: Local file path
            preserve_permissions: Whether to preserve file permissions
        
        Raises:
            RemoteExecutorError: If download fails
        """
        try:
            # Get SSH client
            client = self._get_ssh_client(vm_id)
            
            # Connect if not connected
            if not client._connected:
                client.connect()
            
            # Download file
            client.download_file(remote_path, local_path, preserve_permissions)
            
            # Audit log
            file_size = os.path.getsize(local_path) if os.path.exists(local_path) else 0
            self._audit_log(
                operation='download_file',
                vm_id=vm_id,
                details={
                    'remote_path': remote_path,
                    'local_path': local_path,
                    'file_size': file_size,
                    'preserve_permissions': preserve_permissions,
                },
                status='SUCCESS'
            )
            
        except SSHClientError as e:
            self._audit_log(
                operation='download_file',
                vm_id=vm_id,
                details={'remote_path': remote_path, 'local_path': local_path},
                status='FAILED',
                error=str(e)
            )
            raise RemoteExecutorError(f"Failed to download file from {vm_id}: {e}")
        except Exception as e:
            self._audit_log(
                operation='download_file',
                vm_id=vm_id,
                details={'remote_path': remote_path, 'local_path': local_path},
                status='FAILED',
                error=str(e)
            )
            raise RemoteExecutorError(f"Unexpected error downloading file from {vm_id}: {e}")
    
    def close_connections(self) -> None:
        """Close all SSH connections."""
        for vm_id, client in self._ssh_clients.items():
            try:
                client.disconnect()
            except Exception as e:
                self.logger.warning(f"Error closing connection to {vm_id}: {e}")
        
        self._ssh_clients.clear()
        self.logger.info("All SSH connections closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_connections()
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.close_connections()
        except Exception:
            pass


