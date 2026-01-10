"""
SSH Client wrapper for secure remote connections.

This module provides a secure SSH client wrapper with key-based authentication,
encrypted connections, and comprehensive error handling.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from contextlib import contextmanager

try:
    import paramiko
    from paramiko import SSHClient as ParamikoSSHClient, AutoAddPolicy, RSAKey, Ed25519Key
    from paramiko.ssh_exception import (
        SSHException,
        AuthenticationException,
        NoValidConnectionsError,
        BadHostKeyException
    )
except ImportError:
    raise ImportError(
        "paramiko is required for SSH connections. Install it with: pip install paramiko"
    )


class SSHClientError(Exception):
    """Base exception for SSH client errors."""
    pass


class SSHClient:
    """
    Secure SSH client wrapper with key-based authentication.
    
    Features:
    - Key-based authentication (RSA, Ed25519)
    - Encrypted connections
    - Connection pooling and reuse
    - Comprehensive error handling
    - Audit logging
    """
    
    def __init__(
        self,
        hostname: str,
        username: str,
        port: int = 22,
        key_path: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize SSH client.
        
        Args:
            hostname: Target hostname or IP address
            username: SSH username
            port: SSH port (default: 22)
            key_path: Path to SSH private key file (preferred over password)
            password: SSH password (fallback if key_path not provided)
            timeout: Connection timeout in seconds (default: 30)
            logger: Optional logger instance
        """
        self.hostname = hostname
        self.username = username
        self.port = port
        self.key_path = key_path
        self.password = password
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)
        
        self._client: Optional[ParamikoSSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None
        self._connected = False
        
        # Validate authentication method
        if not key_path and not password:
            raise SSHClientError(
                "Either key_path or password must be provided for authentication"
            )
        
        # Validate key file if provided
        if key_path and not os.path.exists(key_path):
            raise SSHClientError(f"SSH key file not found: {key_path}")
    
    def _load_private_key(self) -> Optional[paramiko.PKey]:
        """
        Load private key from file.
        
        Returns:
            Private key object or None if key_path not provided
        """
        if not self.key_path:
            return None
        
        key_path = Path(self.key_path).expanduser()
        
        # Try different key types
        for key_class, key_type in [(RSAKey, 'RSA'), (Ed25519Key, 'Ed25519')]:
            try:
                return key_class.from_private_key_file(str(key_path))
            except (SSHException, ValueError) as e:
                self.logger.debug(f"Failed to load {key_type} key: {e}")
                continue
        
        # Try generic key loading
        try:
            return paramiko.RSAKey.from_private_key_file(str(key_path))
        except Exception:
            try:
                return paramiko.Ed25519Key.from_private_key_file(str(key_path))
            except Exception as e:
                raise SSHClientError(f"Failed to load SSH key from {key_path}: {e}")
    
    def connect(self) -> None:
        """
        Establish SSH connection.
        
        Raises:
            SSHClientError: If connection fails
        """
        if self._connected and self._client:
            self.logger.debug(f"Already connected to {self.hostname}")
            return
        
        try:
            self._client = ParamikoSSHClient()
            self._client.set_missing_host_key_policy(AutoAddPolicy())
            
            # Prepare authentication
            auth_kwargs = {
                'hostname': self.hostname,
                'port': self.port,
                'username': self.username,
                'timeout': self.timeout,
                'allow_agent': False,  # Disable SSH agent for security
                'look_for_keys': False,  # Only use explicitly provided key
            }
            
            # Add key or password authentication
            pkey = self._load_private_key()
            if pkey:
                auth_kwargs['pkey'] = pkey
                self.logger.info(f"Connecting to {self.hostname} using key-based authentication")
            elif self.password:
                auth_kwargs['password'] = self.password
                self.logger.warning(f"Connecting to {self.hostname} using password authentication (less secure)")
            
            # Establish connection
            self._client.connect(**auth_kwargs)
            self._connected = True
            
            self.logger.info(f"Successfully connected to {self.hostname}:{self.port}")
            
        except AuthenticationException as e:
            self._connected = False
            raise SSHClientError(f"Authentication failed for {self.username}@{self.hostname}: {e}")
        except NoValidConnectionsError as e:
            self._connected = False
            raise SSHClientError(f"Could not connect to {self.hostname}:{self.port}: {e}")
        except BadHostKeyException as e:
            self._connected = False
            raise SSHClientError(f"Host key verification failed for {self.hostname}: {e}")
        except SSHException as e:
            self._connected = False
            raise SSHClientError(f"SSH connection error to {self.hostname}: {e}")
        except Exception as e:
            self._connected = False
            raise SSHClientError(f"Unexpected error connecting to {self.hostname}: {e}")
    
    def disconnect(self) -> None:
        """Close SSH connection."""
        if self._sftp:
            try:
                self._sftp.close()
            except Exception as e:
                self.logger.warning(f"Error closing SFTP connection: {e}")
            self._sftp = None
        
        if self._client:
            try:
                self._client.close()
            except Exception as e:
                self.logger.warning(f"Error closing SSH connection: {e}")
            self._client = None
        
        self._connected = False
        self.logger.debug(f"Disconnected from {self.hostname}")
    
    @contextmanager
    def connection(self):
        """
        Context manager for SSH connection.
        
        Usage:
            with ssh_client.connection():
                ssh_client.execute_command("ls -la")
        """
        try:
            if not self._connected:
                self.connect()
            yield self
        finally:
            # Don't disconnect here - allow connection reuse
            pass
    
    def execute_command(
        self,
        command: str,
        timeout: Optional[int] = None,
        environment: Optional[Dict[str, str]] = None
    ) -> Tuple[int, str, str]:
        """
        Execute command on remote host.
        
        Args:
            command: Command to execute
            timeout: Command timeout in seconds (uses default if None)
            environment: Optional environment variables dict
        
        Returns:
            Tuple of (exit_code, stdout, stderr)
        
        Raises:
            SSHClientError: If execution fails
        """
        if not self._connected or not self._client:
            raise SSHClientError("Not connected. Call connect() first.")
        
        timeout = timeout or self.timeout
        
        try:
            self.logger.info(f"Executing command on {self.hostname}: {command[:100]}")
            
            # Prepare environment if provided
            env_command = ""
            if environment:
                env_vars = " ".join([f"{k}={v}" for k, v in environment.items()])
                env_command = f"export {env_vars} && "
            
            full_command = f"{env_command}{command}"
            
            # Execute command
            stdin, stdout, stderr = self._client.exec_command(
                full_command,
                timeout=timeout
            )
            
            # Read output
            stdout_text = stdout.read().decode('utf-8', errors='replace')
            stderr_text = stderr.read().decode('utf-8', errors='replace')
            exit_code = stdout.channel.recv_exit_status()
            
            self.logger.debug(
                f"Command executed on {self.hostname}. Exit code: {exit_code}"
            )
            
            return exit_code, stdout_text, stderr_text
            
        except SSHException as e:
            raise SSHClientError(f"SSH error executing command on {self.hostname}: {e}")
        except Exception as e:
            raise SSHClientError(f"Unexpected error executing command on {self.hostname}: {e}")
    
    def get_sftp(self) -> paramiko.SFTPClient:
        """
        Get SFTP client for file operations.
        
        Returns:
            SFTP client instance
        
        Raises:
            SSHClientError: If connection not established
        """
        if not self._connected or not self._client:
            raise SSHClientError("Not connected. Call connect() first.")
        
        if not self._sftp:
            try:
                self._sftp = self._client.open_sftp()
            except SSHException as e:
                raise SSHClientError(f"Failed to open SFTP connection: {e}")
        
        return self._sftp
    
    def upload_file(
        self,
        local_path: str,
        remote_path: str,
        preserve_permissions: bool = False
    ) -> None:
        """
        Upload file to remote host.
        
        Args:
            local_path: Local file path
            remote_path: Remote file path
            preserve_permissions: Whether to preserve file permissions
        
        Raises:
            SSHClientError: If upload fails
        """
        if not os.path.exists(local_path):
            raise SSHClientError(f"Local file not found: {local_path}")
        
        try:
            sftp = self.get_sftp()
            
            # Get local file permissions if needed
            local_stat = os.stat(local_path)
            
            self.logger.info(f"Uploading {local_path} to {self.hostname}:{remote_path}")
            
            # Upload file
            sftp.put(local_path, remote_path)
            
            # Preserve permissions if requested
            if preserve_permissions:
                sftp.chmod(remote_path, local_stat.st_mode & 0o777)
            
            self.logger.info(f"Successfully uploaded {local_path} to {remote_path}")
            
        except Exception as e:
            raise SSHClientError(f"Failed to upload file to {self.hostname}: {e}")
    
    def download_file(
        self,
        remote_path: str,
        local_path: str,
        preserve_permissions: bool = False
    ) -> None:
        """
        Download file from remote host.
        
        Args:
            remote_path: Remote file path
            local_path: Local file path
            preserve_permissions: Whether to preserve file permissions
        
        Raises:
            SSHClientError: If download fails
        """
        try:
            sftp = self.get_sftp()
            
            self.logger.info(f"Downloading {self.hostname}:{remote_path} to {local_path}")
            
            # Ensure local directory exists
            local_dir = os.path.dirname(local_path)
            if local_dir:
                os.makedirs(local_dir, exist_ok=True)
            
            # Download file
            sftp.get(remote_path, local_path)
            
            # Preserve permissions if requested
            if preserve_permissions:
                try:
                    remote_stat = sftp.stat(remote_path)
                    os.chmod(local_path, remote_stat.st_mode & 0o777)
                except Exception as e:
                    self.logger.warning(f"Could not preserve permissions: {e}")
            
            self.logger.info(f"Successfully downloaded {remote_path} to {local_path}")
            
        except Exception as e:
            raise SSHClientError(f"Failed to download file from {self.hostname}: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.disconnect()
        except Exception:
            pass

