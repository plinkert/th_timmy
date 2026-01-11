"""
Pytest configuration and fixtures for test suite.
"""

import os
import sys
import tempfile
import shutil
import pytest
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Add automation-scripts to path
automation_scripts_path = project_root / "automation-scripts"
sys.path.insert(0, str(automation_scripts_path))

# Import directly from files, avoiding __init__.py which has problematic imports
# We need to create a proper module structure for relative imports to work
import importlib.util
import types

# Create full package structure
if "automation_scripts" not in sys.modules:
    sys.modules["automation_scripts"] = types.ModuleType("automation_scripts")
    sys.modules["automation_scripts"].__path__ = [str(automation_scripts_path)]
if "automation_scripts.services" not in sys.modules:
    sys.modules["automation_scripts.services"] = types.ModuleType("automation_scripts.services")
    sys.modules["automation_scripts.services"].__path__ = [str(automation_scripts_path / "services")]

# Load ssh_client first (no dependencies on other services)
ssh_client_path = automation_scripts_path / "services" / "ssh_client.py"
ssh_spec = importlib.util.spec_from_file_location("automation_scripts.services.ssh_client", ssh_client_path)
ssh_module = importlib.util.module_from_spec(ssh_spec)
sys.modules["automation_scripts.services.ssh_client"] = ssh_module
ssh_spec.loader.exec_module(ssh_module)
SSHClient = ssh_module.SSHClient
SSHClientError = ssh_module.SSHClientError

# Now load remote_executor
# It uses "from .ssh_client import" which should work now
remote_executor_path = automation_scripts_path / "services" / "remote_executor.py"
remote_spec = importlib.util.spec_from_file_location("automation_scripts.services.remote_executor", remote_executor_path)
remote_module = importlib.util.module_from_spec(remote_spec)
sys.modules["automation_scripts.services.remote_executor"] = remote_module

# Execute the module - it will import from .ssh_client which is already loaded
remote_spec.loader.exec_module(remote_module)
RemoteExecutor = remote_module.RemoteExecutor
RemoteExecutorError = remote_module.RemoteExecutorError


@pytest.fixture(scope="session")
def project_root_path():
    """Return project root path."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def project_root_path():
    """Return project root path."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def test_config(project_root_path) -> Dict[str, Any]:
    """Load test configuration from config.yml."""
    config_path = project_root_path / "configs" / "config.yml"
    
    if not config_path.exists():
        pytest.skip("config.yml not found. Please create it from config.example.yml")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config


@pytest.fixture(scope="session")
def vm_configs(test_config) -> Dict[str, Dict[str, Any]]:
    """Extract VM configurations from test config."""
    return test_config.get('vms', {})


@pytest.fixture(scope="session")
def ssh_key_path() -> Optional[str]:
    """Get SSH key path from environment or default locations."""
    # Check environment variable
    key_path = os.getenv('SSH_KEY_PATH')
    if key_path and os.path.exists(key_path):
        return key_path
    
    # Check default locations
    home = Path.home()
    default_keys = [
        home / '.ssh' / 'id_rsa',
        home / '.ssh' / 'id_ed25519',
        home / '.ssh' / 'id_rsa_th',
    ]
    
    for key in default_keys:
        if key.exists():
            return str(key)
    
    # If no key found, return None (will use password if available)
    return None


@pytest.fixture(scope="session")
def ssh_password() -> Optional[str]:
    """Get SSH password from environment."""
    return os.getenv('SSH_PASSWORD')


@pytest.fixture(scope="function")
def temp_dir():
    """Create temporary directory for test files."""
    temp_path = tempfile.mkdtemp(prefix="th_test_")
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture(scope="function")
def test_file(temp_dir):
    """Create test file with content."""
    test_file_path = os.path.join(temp_dir, "test.txt")
    with open(test_file_path, 'w') as f:
        f.write("test content")
    return test_file_path


@pytest.fixture(scope="function")
def test_script(temp_dir):
    """Create test bash script."""
    script_path = os.path.join(temp_dir, "test_script.sh")
    with open(script_path, 'w') as f:
        f.write("#!/bin/bash\n")
        f.write("date\n")
    os.chmod(script_path, 0o755)
    return script_path


@pytest.fixture(scope="function")
def remote_executor(test_config, ssh_key_path, ssh_password, temp_dir):
    """Create RemoteExecutor instance for testing."""
    audit_log_path = os.path.join(temp_dir, "audit.log")
    
    executor = RemoteExecutor(
        config=test_config,
        ssh_key_path=ssh_key_path,
        ssh_password=ssh_password,
        audit_log_path=audit_log_path
    )
    
    yield executor
    
    # Cleanup
    executor.close_connections()


@pytest.fixture(scope="function")
def ssh_client_vm01(vm_configs, ssh_key_path, ssh_password):
    """Create SSH client for VM01."""
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
    
    yield client
    
    # Cleanup
    client.disconnect()


@pytest.fixture(scope="function")
def ssh_client_vm02(vm_configs, ssh_key_path, ssh_password):
    """Create SSH client for VM02."""
    if 'vm02' not in vm_configs:
        pytest.skip("VM02 not configured")
    
    vm_config = vm_configs['vm02']
    client = SSHClient(
        hostname=vm_config['ip'],
        username=vm_config.get('ssh_user', 'thadmin'),
        port=vm_config.get('ssh_port', 22),
        key_path=ssh_key_path,
        password=ssh_password,
        timeout=30
    )
    
    yield client
    
    # Cleanup
    client.disconnect()


@pytest.fixture(scope="function")
def ssh_client_vm03(vm_configs, ssh_key_path, ssh_password):
    """Create SSH client for VM03."""
    if 'vm03' not in vm_configs:
        pytest.skip("VM03 not configured")
    
    vm_config = vm_configs['vm03']
    client = SSHClient(
        hostname=vm_config['ip'],
        username=vm_config.get('ssh_user', 'thadmin'),
        port=vm_config.get('ssh_port', 22),
        key_path=ssh_key_path,
        password=ssh_password,
        timeout=30
    )
    
    yield client
    
    # Cleanup
    client.disconnect()


@pytest.fixture(scope="function")
def all_vm_ids(vm_configs):
    """Return list of all enabled VM IDs."""
    return [vm_id for vm_id, config in vm_configs.items() if config.get('enabled', True)]


@pytest.fixture(scope="function")
def skip_if_no_ssh_key(ssh_key_path, ssh_password):
    """Skip test if no SSH authentication available."""
    if not ssh_key_path and not ssh_password:
        pytest.skip("No SSH key or password available for authentication")


@pytest.fixture(scope="function")
def skip_if_vm_unreachable(vm_configs):
    """Skip test if VMs are not reachable (basic connectivity check)."""
    import socket
    
    for vm_id, config in vm_configs.items():
        if not config.get('enabled', True):
            continue
        
        ip = config.get('ip')
        port = config.get('ssh_port', 22)
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((ip, port))
            sock.close()
        except Exception:
            pytest.skip(f"VM {vm_id} ({ip}) is not reachable")


@pytest.fixture(scope="function")
def repo_sync_service(test_config, remote_executor, project_root_path):
    """Create RepoSyncService instance for testing."""
    # Ensure repository config exists
    # Use /home/thadmin/th_timmy on VMs (where repo actually is)
    vm_repo_path = '/home/thadmin/th_timmy'
    
    if 'repository' not in test_config:
        # Add default repository config
        test_config['repository'] = {
            'main_repo_path': str(project_root_path),  # Local path for VM04
            'vm_repo_paths': {
                'vm01': vm_repo_path,
                'vm02': vm_repo_path,
                'vm03': vm_repo_path,
                'vm04': vm_repo_path,
            },
            'branch': 'main',
            'auto_sync': False
        }
    else:
        # Update paths if they're relative or use defaults
        repo_config = test_config['repository']
        if 'vm_repo_paths' not in repo_config:
            repo_config['vm_repo_paths'] = {
                'vm01': vm_repo_path,
                'vm02': vm_repo_path,
                'vm03': vm_repo_path,
                'vm04': vm_repo_path,
            }
        # Update main_repo_path if not set
        if 'main_repo_path' not in repo_config:
            repo_config['main_repo_path'] = str(project_root_path)
    
    # Import RepoSyncService
    import importlib.util
    import types
    
    automation_scripts_path = project_root_path / "automation-scripts"
    
    # Create package structure if needed
    if "automation_scripts.services" not in sys.modules:
        sys.modules["automation_scripts.services"] = types.ModuleType("automation_scripts.services")
    
    # Load repo_sync
    repo_sync_path = automation_scripts_path / "services" / "repo_sync.py"
    repo_sync_spec = importlib.util.spec_from_file_location("automation_scripts.services.repo_sync", repo_sync_path)
    repo_sync_module = importlib.util.module_from_spec(repo_sync_spec)
    sys.modules["automation_scripts.services.repo_sync"] = repo_sync_module
    
    # Inject dependencies
    repo_sync_module.RemoteExecutor = RemoteExecutor
    repo_sync_module.RemoteExecutorError = RemoteExecutorError
    
    # Load utils.git_manager if needed
    try:
        git_manager_path = automation_scripts_path / "utils" / "git_manager.py"
        if git_manager_path.exists():
            git_manager_spec = importlib.util.spec_from_file_location("automation_scripts.utils.git_manager", git_manager_path)
            git_manager_module = importlib.util.module_from_spec(git_manager_spec)
            sys.modules["automation_scripts.utils"] = types.ModuleType("automation_scripts.utils")
            sys.modules["automation_scripts.utils.git_manager"] = git_manager_module
            git_manager_spec.loader.exec_module(git_manager_module)
            repo_sync_module.GitManager = git_manager_module.GitManager
            repo_sync_module.GitManagerError = git_manager_module.GitManagerError
    except Exception as e:
        # GitManager might not be available, that's OK for some tests
        pass
    
    repo_sync_spec.loader.exec_module(repo_sync_module)
    RepoSyncService = repo_sync_module.RepoSyncService
    
    # Create service instance
    service = RepoSyncService(
        config=test_config,
        remote_executor=remote_executor
    )
    
    yield service
    
    # Cleanup
    service.close()

