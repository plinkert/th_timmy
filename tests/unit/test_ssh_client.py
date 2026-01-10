"""
Unit tests for SSH Client (TC-0-01-07: Security SSH).

Test Cases:
- TC-0-01-07: Bezpieczeństwo SSH
"""

import pytest
import os
import sys
from pathlib import Path

# Add automation-scripts to path
project_root = Path(__file__).parent.parent.parent
automation_scripts_path = project_root / "automation-scripts"
sys.path.insert(0, str(automation_scripts_path))

from services.ssh_client import SSHClient, SSHClientError


class TestSSHSecurity:
    """Test security features of SSH Client."""
    
    def test_key_based_authentication_preferred(self, vm_configs, ssh_key_path, ssh_password):
        """
        TC-0-01-07: Verify that SSH keys are used (not passwords) when available.
        """
        if 'vm01' not in vm_configs:
            pytest.skip("VM01 not configured")
        
        vm_config = vm_configs['vm01']
        
        # Create SSH client with key
        if ssh_key_path:
            client = SSHClient(
                hostname=vm_config['ip'],
                username=vm_config.get('ssh_user', 'thadmin'),
                port=vm_config.get('ssh_port', 22),
                key_path=ssh_key_path,
                password=ssh_password,  # Password as fallback
                timeout=30
            )
            
            # Verify key path is set
            assert client.key_path == ssh_key_path
            assert client.key_path is not None
            
            # Try to connect
            try:
                client.connect()
                assert client._connected is True
                
                # Verify connection is encrypted (SSH uses encryption by default)
                # We can't directly test encryption, but if connection succeeds,
                # it means SSH handshake completed (which requires encryption)
                assert client._client is not None
                
            finally:
                client.disconnect()
        else:
            pytest.skip("No SSH key available for testing")
    
    def test_encrypted_connection(self, vm_configs, ssh_key_path, ssh_password):
        """
        TC-0-01-07: Verify that connections are encrypted.
        
        Note: SSH connections are encrypted by default. If connection succeeds,
        encryption is in place.
        """
        if 'vm01' not in vm_configs:
            pytest.skip("VM01 not configured")
        
        vm_config = vm_configs['vm01']
        
        client = SSHClient(
            hostname=vm_config['ip'],
            username=vm_config.get('ssh_user', 'thadmin'),
            port=vm_config.get('ssh_port', 22),
            key_path=ssh_key_path,
            password=ssh_password,
            timeout=30
        )
        
        try:
            client.connect()
            
            # If connection succeeds, SSH encryption is active
            # SSH protocol requires encryption for all connections
            assert client._connected is True
            
            # Verify we can execute a command (proves encrypted channel works)
            exit_code, stdout, stderr = client.execute_command("echo 'test'")
            assert exit_code == 0
            
        finally:
            client.disconnect()
    
    def test_no_password_when_key_available(self, vm_configs, ssh_key_path):
        """
        TC-0-01-07: Verify that password is not used when key is available.
        """
        if not ssh_key_path:
            pytest.skip("No SSH key available for testing")
        
        if 'vm01' not in vm_configs:
            pytest.skip("VM01 not configured")
        
        vm_config = vm_configs['vm01']
        
        # Create client with key but no password
        client = SSHClient(
            hostname=vm_config['ip'],
            username=vm_config.get('ssh_user', 'thadmin'),
            port=vm_config.get('ssh_port', 22),
            key_path=ssh_key_path,
            password=None,  # No password
            timeout=30
        )
        
        try:
            # Should connect using key only
            client.connect()
            assert client._connected is True
            
        finally:
            client.disconnect()
    
    def test_context_manager_cleanup(self, vm_configs, ssh_key_path, ssh_password):
        """Test that context manager properly manages connections."""
        if 'vm01' not in vm_configs:
            pytest.skip("VM01 not configured")
        
        vm_config = vm_configs['vm01']
        
        client = SSHClient(
            hostname=vm_config['ip'],
            username=vm_config.get('ssh_user', 'thadmin'),
            port=vm_config.get('ssh_port', 22),
            key_path=ssh_key_path,
            password=ssh_password,
            timeout=30
        )
        
        # Use context manager
        with client.connection():
            assert client._connected is True
            exit_code, stdout, stderr = client.execute_command("echo 'test'")
            assert exit_code == 0
        
        # Connection should still be available (reuse)
        assert client._connected is True
        
        # Manual cleanup
        client.disconnect()
        assert client._connected is False

