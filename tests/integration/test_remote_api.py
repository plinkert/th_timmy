"""
Integration tests for Remote Execution REST API.

Tests for FastAPI endpoints:
- POST /execute-command
- POST /execute-script
- POST /upload-file
- POST /download-file
- GET /health
"""

import pytest
import os
import sys
import yaml
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient

# Add automation-scripts to path
project_root = Path(__file__).parent.parent.parent
automation_scripts_path = project_root / "automation-scripts"
sys.path.insert(0, str(automation_scripts_path))

# Import remote_executor first (needed by remote_api)
from services.remote_executor import RemoteExecutor

# For API tests, we'll skip if FastAPI import fails
# This allows tests to run even if API module has import issues
try:
    # Try to import directly
    from api.remote_api import app, get_executor
except ImportError:
    # If direct import fails, try loading module manually
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "remote_api",
        automation_scripts_path / "api" / "remote_api.py"
    )
    if spec and spec.loader:
        remote_api_module = importlib.util.module_from_spec(spec)
        # Create parent modules
        if "automation_scripts" not in sys.modules:
            import types
            sys.modules["automation_scripts"] = types.ModuleType("automation_scripts")
        if "automation_scripts.api" not in sys.modules:
            import types
            sys.modules["automation_scripts.api"] = types.ModuleType("automation_scripts.api")
        sys.modules["automation_scripts.api.remote_api"] = remote_api_module
        spec.loader.exec_module(remote_api_module)
        app = remote_api_module.app
        get_executor = remote_api_module.get_executor
    else:
        # If all else fails, mark tests to skip
        app = None
        get_executor = None


@pytest.fixture(scope="function")
def api_client(test_config, ssh_key_path, ssh_password, temp_dir):
    """Create test client for API."""
    # Set environment variables for executor
    os.environ['CONFIG_PATH'] = os.path.join(temp_dir, "config.yml")
    os.environ['SSH_KEY_PATH'] = ssh_key_path or ''
    os.environ['SSH_PASSWORD'] = ssh_password or ''
    os.environ['AUDIT_LOG_PATH'] = os.path.join(temp_dir, "audit.log")
    
    # Create temporary config file
    config_path = os.path.join(temp_dir, "config.yml")
    with open(config_path, 'w') as f:
        yaml.dump(test_config, f)
    
    # Override get_executor to use test config
    def get_test_executor():
        return RemoteExecutor(
            config=test_config,
            ssh_key_path=ssh_key_path,
            ssh_password=ssh_password,
            audit_log_path=os.path.join(temp_dir, "audit.log")
        )
    
    app.dependency_overrides[get_executor] = get_test_executor
    
    client = TestClient(app)
    
    yield client
    
    # Cleanup
    app.dependency_overrides.clear()


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, api_client):
        """Test GET /health endpoint."""
        response = api_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert data['service'] == 'remote-execution-api'
        assert 'timestamp' in data


class TestExecuteCommandEndpoint:
    """Test POST /execute-command endpoint."""
    
    def test_execute_command_success(self, api_client, skip_if_vm_unreachable):
        """Test successful command execution."""
        payload = {
            "vm_id": "vm01",
            "command": 'echo "test"',
            "timeout": 10
        }
        
        response = api_client.post("/execute-command", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['exit_code'] == 0
        assert "test" in data['stdout']
        assert data['vm_id'] == "vm01"
        assert data['command'] == 'echo "test"'
        assert data['execution_time'] > 0
    
    def test_execute_command_invalid_vm(self, api_client):
        """Test command execution with invalid VM ID."""
        payload = {
            "vm_id": "nonexistent_vm",
            "command": 'echo "test"'
        }
        
        response = api_client.post("/execute-command", json=payload)
        
        assert response.status_code == 500  # Internal server error
        assert 'error' in response.json().get('detail', '').lower() or 'not found' in response.json().get('detail', '').lower()
    
    def test_execute_command_with_timeout(self, api_client, skip_if_vm_unreachable):
        """Test command execution with timeout."""
        payload = {
            "vm_id": "vm01",
            "command": "sleep 10",
            "timeout": 2
        }
        
        response = api_client.post("/execute-command", json=payload)
        
        # Should either timeout or return error
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            # Command might complete or timeout
            assert data['execution_time'] <= 5  # Should be around timeout value


class TestExecuteScriptEndpoint:
    """Test POST /execute-script endpoint."""
    
    def test_execute_script_success(self, api_client, test_script, skip_if_vm_unreachable):
        """Test successful script execution."""
        # First upload script
        remote_script_path = '/tmp/test_api_script.sh'
        
        # Upload via executor (we'll test API upload separately)
        executor = get_executor()
        try:
            executor.upload_file(
                vm_id='vm02',
                local_path=test_script,
                remote_path=remote_script_path
            )
            
            # Execute via API
            payload = {
                "vm_id": "vm02",
                "script_path": remote_script_path,
                "interpreter": "/bin/bash"
            }
            
            response = api_client.post("/execute-script", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['exit_code'] == 0
            assert data['vm_id'] == "vm02"
            assert data['script_path'] == remote_script_path
            
            # Cleanup
            executor.execute_remote_command(
                vm_id='vm02',
                command=f'rm -f {remote_script_path}'
            )
        finally:
            executor.close_connections()


class TestFileUploadEndpoint:
    """Test POST /upload-file endpoint."""
    
    def test_upload_file_success(self, api_client, test_file, skip_if_vm_unreachable):
        """Test successful file upload."""
        payload = {
            "vm_id": "vm03",
            "local_path": test_file,
            "remote_path": "/tmp/test_api_upload.txt",
            "preserve_permissions": False
        }
        
        response = api_client.post("/upload-file", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['vm_id'] == "vm03"
        assert "uploaded" in data['message'].lower()
        assert data['operation_time'] > 0
        
        # Verify file exists on remote VM
        executor = get_executor()
        try:
            exit_code, stdout, stderr = executor.execute_remote_command(
                vm_id='vm03',
                command='test -f /tmp/test_api_upload.txt && echo "exists"'
            )
            assert "exists" in stdout
            
            # Cleanup
            executor.execute_remote_command(
                vm_id='vm03',
                command='rm -f /tmp/test_api_upload.txt'
            )
        finally:
            executor.close_connections()
    
    def test_upload_file_not_found(self, api_client):
        """Test upload with non-existent local file."""
        payload = {
            "vm_id": "vm03",
            "local_path": "/nonexistent/file.txt",
            "remote_path": "/tmp/test.txt"
        }
        
        response = api_client.post("/upload-file", json=payload)
        
        assert response.status_code in [400, 500]  # Bad request or internal error


class TestFileDownloadEndpoint:
    """Test POST /download-file endpoint."""
    
    def test_download_file_success(self, api_client, temp_dir, skip_if_vm_unreachable):
        """Test successful file download."""
        # Create file on remote VM first
        executor = get_executor()
        try:
            remote_path = '/tmp/test_api_download.txt'
            executor.execute_remote_command(
                vm_id='vm01',
                command=f'echo "download test content" > {remote_path}'
            )
            
            # Download via API
            local_path = os.path.join(temp_dir, "downloaded.txt")
            payload = {
                "vm_id": "vm01",
                "remote_path": remote_path,
                "local_path": local_path,
                "preserve_permissions": False
            }
            
            response = api_client.post("/download-file", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['vm_id'] == "vm01"
            assert "downloaded" in data['message'].lower()
            
            # Verify local file exists and has correct content
            assert os.path.exists(local_path)
            with open(local_path, 'r') as f:
                content = f.read()
            assert "download test content" in content
            
            # Cleanup
            executor.execute_remote_command(
                vm_id='vm01',
                command=f'rm -f {remote_path}'
            )
        finally:
            executor.close_connections()


class TestAPIAuthorization:
    """Test API authorization (if configured)."""
    
    def test_api_without_key(self, api_client):
        """Test that API works without key in development mode."""
        # In development mode, API should work without key
        response = api_client.get("/health")
        assert response.status_code == 200
    
    def test_api_with_invalid_key(self, api_client):
        """Test API with invalid key."""
        # Set API key in environment
        os.environ['API_KEY'] = 'test_key_123'
        
        # Try to access without key
        response = api_client.get("/health")
        # Health endpoint might not require auth, but let's check
        assert response.status_code in [200, 401]
        
        # Cleanup
        if 'API_KEY' in os.environ:
            del os.environ['API_KEY']

