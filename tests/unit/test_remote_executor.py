"""
Unit tests for Remote Executor.

Test Cases:
- TC-0-01-01: Podstawowe wykonanie komendy
- TC-0-01-02: Wykonanie skryptu na zdalnym VM
- TC-0-01-03: Upload pliku
- TC-0-01-04: Download pliku
- TC-0-01-05: Timeout komendy
- TC-0-01-06: Błędna komenda
"""

import pytest
import time
import os
import sys
from pathlib import Path

# Add automation-scripts to path
project_root = Path(__file__).parent.parent.parent
automation_scripts_path = project_root / "automation-scripts"
sys.path.insert(0, str(automation_scripts_path))

from services.remote_executor import RemoteExecutor, RemoteExecutorError


class TestBasicCommandExecution:
    """TC-0-01-01: Podstawowe wykonanie komendy"""
    
    def test_execute_simple_command(self, remote_executor, skip_if_vm_unreachable):
        """
        TC-0-01-01: Execute basic command on VM01.
        
        Expected: Command executed in < 5 seconds, correct output returned.
        """
        start_time = time.time()
        
        exit_code, stdout, stderr = remote_executor.execute_remote_command(
            vm_id='vm01',
            command='echo "test"'
        )
        
        execution_time = time.time() - start_time
        
        # Verify results
        assert exit_code == 0, f"Command failed with exit code {exit_code}"
        assert "test" in stdout.strip(), f"Expected 'test' in output, got: {stdout}"
        assert execution_time < 5.0, f"Command took too long: {execution_time:.2f}s"
    
    def test_execute_command_with_output(self, remote_executor, skip_if_vm_unreachable):
        """Test command execution with various outputs."""
        # Test date command
        exit_code, stdout, stderr = remote_executor.execute_remote_command(
            vm_id='vm01',
            command='date'
        )
        assert exit_code == 0
        assert len(stdout) > 0  # Should have date output
        
        # Test whoami
        exit_code, stdout, stderr = remote_executor.execute_remote_command(
            vm_id='vm01',
            command='whoami'
        )
        assert exit_code == 0
        assert len(stdout.strip()) > 0
        
        # Test pwd
        exit_code, stdout, stderr = remote_executor.execute_remote_command(
            vm_id='vm01',
            command='pwd'
        )
        assert exit_code == 0
        assert '/' in stdout  # Should contain path


class TestScriptExecution:
    """TC-0-01-02: Wykonanie skryptu na zdalnym VM"""
    
    def test_execute_remote_script(self, remote_executor, test_script, skip_if_vm_unreachable):
        """
        TC-0-01-02: Execute script on VM02.
        
        Steps:
        1. Upload test script to VM02
        2. Execute script via Remote Execution Service
        3. Check output
        
        Expected: Script executed, date returned.
        """
        # First, upload the script
        remote_script_path = '/tmp/test_script.sh'
        remote_executor.upload_file(
            vm_id='vm02',
            local_path=test_script,
            remote_path=remote_script_path
        )
        
        # Execute the script
        exit_code, stdout, stderr = remote_executor.execute_remote_script(
            vm_id='vm02',
            script_path=remote_script_path
        )
        
        # Verify results
        assert exit_code == 0, f"Script failed with exit code {exit_code}"
        assert len(stdout) > 0, "Script should return date output"
        # Date output should contain date-like information
        assert any(char.isdigit() for char in stdout), "Output should contain date information"
        
        # Cleanup
        remote_executor.execute_remote_command(
            vm_id='vm02',
            command=f'rm -f {remote_script_path}'
        )


class TestFileUpload:
    """TC-0-01-03: Upload pliku"""
    
    def test_upload_file(self, remote_executor, test_file, skip_if_vm_unreachable):
        """
        TC-0-01-03: Upload file to VM03.
        
        Steps:
        1. Prepare test file with content "test content"
        2. Upload file to VM03 at /tmp/test.txt
        3. Execute cat /tmp/test.txt on VM03
        4. Check output
        
        Expected: File uploaded, content correct.
        """
        remote_path = '/tmp/test.txt'
        
        # Upload file
        remote_executor.upload_file(
            vm_id='vm03',
            local_path=test_file,
            remote_path=remote_path
        )
        
        # Verify file exists and content is correct
        exit_code, stdout, stderr = remote_executor.execute_remote_command(
            vm_id='vm03',
            command=f'cat {remote_path}'
        )
        
        assert exit_code == 0, "Failed to read uploaded file"
        assert "test content" in stdout, f"Expected 'test content', got: {stdout}"
        
        # Cleanup
        remote_executor.execute_remote_command(
            vm_id='vm03',
            command=f'rm -f {remote_path}'
        )


class TestFileDownload:
    """TC-0-01-04: Download pliku"""
    
    def test_download_file(self, remote_executor, temp_dir, skip_if_vm_unreachable):
        """
        TC-0-01-04: Download file from VM01.
        
        Steps:
        1. Create file on VM01: echo "remote content" > /tmp/remote.txt
        2. Download file from VM01 to local /tmp/local.txt
        3. Check local file content
        
        Expected: File downloaded, content correct.
        """
        remote_path = '/tmp/remote.txt'
        local_path = os.path.join(temp_dir, 'local.txt')
        
        # Create file on remote VM
        remote_executor.execute_remote_command(
            vm_id='vm01',
            command=f'echo "remote content" > {remote_path}'
        )
        
        # Download file
        remote_executor.download_file(
            vm_id='vm01',
            remote_path=remote_path,
            local_path=local_path
        )
        
        # Verify local file exists and content is correct
        assert os.path.exists(local_path), "Downloaded file does not exist"
        
        with open(local_path, 'r') as f:
            content = f.read()
        
        assert "remote content" in content, f"Expected 'remote content', got: {content}"
        
        # Cleanup remote file
        remote_executor.execute_remote_command(
            vm_id='vm01',
            command=f'rm -f {remote_path}'
        )


class TestCommandTimeout:
    """TC-0-01-05: Timeout komendy"""
    
    def test_command_timeout(self, remote_executor, skip_if_vm_unreachable):
        """
        TC-0-01-05: Verify command timeout handling.
        
        Steps:
        1. Execute command sleep 10 with timeout=5 seconds
        2. Check if command was interrupted
        
        Expected: Command interrupted after 5 seconds, error returned.
        """
        timeout = 5
        
        start_time = time.time()
        
        # Execute command that should timeout
        with pytest.raises((RemoteExecutorError, Exception)) as exc_info:
            remote_executor.execute_remote_command(
                vm_id='vm01',
                command='sleep 10',
                timeout=timeout
            )
        
        execution_time = time.time() - start_time
        
        # Verify timeout occurred
        assert execution_time < 10, "Command should have been interrupted"
        assert execution_time >= timeout - 1, f"Timeout should be at least {timeout-1}s, got {execution_time:.2f}s"
        assert execution_time <= timeout + 2, f"Timeout should be at most {timeout+2}s, got {execution_time:.2f}s"
        
        # Verify error was raised
        assert exc_info.value is not None


class TestErrorHandling:
    """TC-0-01-06: Błędna komenda"""
    
    def test_nonexistent_command(self, remote_executor, skip_if_vm_unreachable):
        """
        TC-0-01-06: Verify error handling for invalid commands.
        
        Steps:
        1. Execute non-existent command: nonexistent_command
        2. Check returned error
        
        Expected: Error returned, informative message, logs saved.
        """
        exit_code, stdout, stderr = remote_executor.execute_remote_command(
            vm_id='vm01',
            command='nonexistent_command_xyz123'
        )
        
        # Command should fail (non-zero exit code)
        assert exit_code != 0, "Non-existent command should return non-zero exit code"
        
        # Should have error message in stderr
        assert len(stderr) > 0, "Should have error message in stderr"
        
        # Common error messages
        assert any(keyword in stderr.lower() for keyword in ['not found', 'command not found', 'no such file']), \
            f"Expected error message, got: {stderr}"
    
    def test_invalid_vm_id(self, remote_executor):
        """Test error handling for invalid VM ID."""
        with pytest.raises(RemoteExecutorError) as exc_info:
            remote_executor.execute_remote_command(
                vm_id='nonexistent_vm',
                command='echo "test"'
            )
        
        # The error message should contain "not found" or "nonexistent"
        # RemoteExecutor wraps errors, so check for either the original or wrapped message
        error_msg = str(exc_info.value).lower()
        # Message is: "Unexpected error executing command on nonexistent_vm: VM 'nonexistent_vm' not found in configuration"
        has_nonexistent = "nonexistent" in error_msg
        has_not_found = "not found" in error_msg
        if not (has_nonexistent and has_not_found):
            # Debug output
            print(f"DEBUG: error_msg = '{error_msg}'")
            print(f"DEBUG: has_nonexistent = {has_nonexistent}")
            print(f"DEBUG: has_not_found = {has_not_found}")
        assert (has_nonexistent and has_not_found), \
            f"Expected error message about VM not found, got: {error_msg}"
    
    def test_audit_logging(self, remote_executor, temp_dir, skip_if_vm_unreachable):
        """Verify that audit logging works."""
        audit_log_path = os.path.join(temp_dir, "audit.log")
        
        # Create new executor with specific audit log
        executor = RemoteExecutor(
            config=remote_executor.config,
            ssh_key_path=remote_executor.ssh_key_path,
            ssh_password=remote_executor.ssh_password,
            audit_log_path=audit_log_path
        )
        
        try:
            # Execute a command
            executor.execute_remote_command(
                vm_id='vm01',
                command='echo "audit test"'
            )
            
            # Verify audit log was created
            assert os.path.exists(audit_log_path), "Audit log file should exist"
            
            # Verify audit log contains entry
            with open(audit_log_path, 'r') as f:
                log_content = f.read()
            
            assert 'execute_remote_command' in log_content
            assert 'vm01' in log_content
            assert 'SUCCESS' in log_content or 'FAILED' in log_content
            
        finally:
            executor.close_connections()

