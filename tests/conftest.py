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
    automation_scripts_module = types.ModuleType("automation_scripts")
    automation_scripts_module.__path__ = [str(automation_scripts_path)]
    sys.modules["automation_scripts"] = automation_scripts_module
else:
    automation_scripts_module = sys.modules["automation_scripts"]

if "automation_scripts.services" not in sys.modules:
    services_module = types.ModuleType("automation_scripts.services")
    services_module.__path__ = [str(automation_scripts_path / "services")]
    sys.modules["automation_scripts.services"] = services_module
    automation_scripts_module.services = services_module

if "automation_scripts.utils" not in sys.modules:
    utils_module = types.ModuleType("automation_scripts.utils")
    utils_module.__path__ = [str(automation_scripts_path / "utils")]
    sys.modules["automation_scripts.utils"] = utils_module
    automation_scripts_module.utils = utils_module

if "automation_scripts.orchestrators" not in sys.modules:
    orchestrators_module = types.ModuleType("automation_scripts.orchestrators")
    orchestrators_module.__path__ = [str(automation_scripts_path / "orchestrators")]
    sys.modules["automation_scripts.orchestrators"] = orchestrators_module
    automation_scripts_module.orchestrators = orchestrators_module

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


@pytest.fixture(scope="function")
def temp_dir():
    """Create temporary directory for tests."""
    import tempfile
    import shutil
    
    temp_path = tempfile.mkdtemp()
    yield temp_path
    
    # Cleanup
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture(scope="function")
def config_manager(test_config, remote_executor, project_root_path, temp_dir):
    """Create ConfigManager instance for testing."""
    # Import ConfigManager
    import importlib.util
    import types
    
    automation_scripts_path = project_root_path / "automation-scripts"
    
    # Create package structure if needed
    if "automation_scripts.services" not in sys.modules:
        sys.modules["automation_scripts.services"] = types.ModuleType("automation_scripts.services")
    
    # Load config_manager
    config_manager_path = automation_scripts_path / "services" / "config_manager.py"
    config_manager_spec = importlib.util.spec_from_file_location("automation_scripts.services.config_manager", config_manager_path)
    config_manager_module = importlib.util.module_from_spec(config_manager_spec)
    sys.modules["automation_scripts.services.config_manager"] = config_manager_module
    
    # Inject dependencies
    config_manager_module.RemoteExecutor = RemoteExecutor
    config_manager_module.RemoteExecutorError = RemoteExecutorError
    
    # Load utils modules
    try:
        # Load config_validator
        validator_path = automation_scripts_path / "utils" / "config_validator.py"
        if validator_path.exists():
            validator_spec = importlib.util.spec_from_file_location("automation_scripts.utils.config_validator", validator_path)
            validator_module = importlib.util.module_from_spec(validator_spec)
            sys.modules["automation_scripts.utils"] = types.ModuleType("automation_scripts.utils")
            sys.modules["automation_scripts.utils.config_validator"] = validator_module
            validator_spec.loader.exec_module(validator_module)
            config_manager_module.ConfigValidator = validator_module.ConfigValidator
            config_manager_module.ConfigValidatorError = validator_module.ConfigValidatorError
        
        # Load config_backup
        backup_path = automation_scripts_path / "utils" / "config_backup.py"
        if backup_path.exists():
            backup_spec = importlib.util.spec_from_file_location("automation_scripts.utils.config_backup", backup_path)
            backup_module = importlib.util.module_from_spec(backup_spec)
            sys.modules["automation_scripts.utils.config_backup"] = backup_module
            backup_spec.loader.exec_module(backup_module)
            config_manager_module.ConfigBackup = backup_module.ConfigBackup
            config_manager_module.ConfigBackupError = backup_module.ConfigBackupError
    except Exception as e:
        # Utils might not be available, that's OK for some tests
        pass
    
    config_manager_spec.loader.exec_module(config_manager_module)
    ConfigManager = config_manager_module.ConfigManager
    
    # Add config_management section to test_config if not present
    if 'config_management' not in test_config:
        test_config['config_management'] = {
            'paths': {
                'central': 'configs/config.yml',
                'vm': {
                    'vm01': 'configs/config.yml',
                    'vm02': 'configs/config.yml',
                    'vm03': 'configs/config.yml',
                    'vm04': 'configs/config.yml',
                }
            },
            'backup_dir': os.path.join(temp_dir, 'backups'),
            'history_file': os.path.join(temp_dir, 'config_history.json')
        }
    
    # Create service instance
    service = ConfigManager(
        config=test_config,
        remote_executor=remote_executor,
        backup_dir=os.path.join(temp_dir, 'backups'),
        history_file=os.path.join(temp_dir, 'config_history.json')
    )
    
    yield service
    
    # Cleanup
    service.close()


@pytest.fixture(scope="function")
def health_monitor(test_config, remote_executor, project_root_path, temp_dir):
    """Create HealthMonitor instance for testing."""
    # Import HealthMonitor
    import importlib.util
    import types
    
    automation_scripts_path = project_root_path / "automation-scripts"
    
    # Create package structure if needed
    if "automation_scripts.services" not in sys.modules:
        sys.modules["automation_scripts.services"] = types.ModuleType("automation_scripts.services")
    
    # Load health_monitor
    health_monitor_path = automation_scripts_path / "services" / "health_monitor.py"
    health_monitor_spec = importlib.util.spec_from_file_location("automation_scripts.services.health_monitor", health_monitor_path)
    health_monitor_module = importlib.util.module_from_spec(health_monitor_spec)
    sys.modules["automation_scripts.services.health_monitor"] = health_monitor_module
    
    # Inject dependencies
    health_monitor_module.RemoteExecutor = RemoteExecutor
    health_monitor_module.RemoteExecutorError = RemoteExecutorError
    
    # Load metrics_collector
    try:
        metrics_path = automation_scripts_path / "services" / "metrics_collector.py"
        if metrics_path.exists():
            metrics_spec = importlib.util.spec_from_file_location("automation_scripts.services.metrics_collector", metrics_path)
            metrics_module = importlib.util.module_from_spec(metrics_spec)
            sys.modules["automation_scripts.services.metrics_collector"] = metrics_module
            metrics_spec.loader.exec_module(metrics_module)
            health_monitor_module.MetricsCollector = metrics_module.MetricsCollector
            health_monitor_module.MetricsCollectorError = metrics_module.MetricsCollectorError
    except Exception as e:
        pass
    
    # Load alert_manager
    try:
        alert_path = automation_scripts_path / "utils" / "alert_manager.py"
        if alert_path.exists():
            alert_spec = importlib.util.spec_from_file_location("automation_scripts.utils.alert_manager", alert_path)
            alert_module = importlib.util.module_from_spec(alert_spec)
            if "automation_scripts.utils" not in sys.modules:
                sys.modules["automation_scripts.utils"] = types.ModuleType("automation_scripts.utils")
            sys.modules["automation_scripts.utils.alert_manager"] = alert_module
            alert_spec.loader.exec_module(alert_module)
            health_monitor_module.AlertManager = alert_module.AlertManager
            health_monitor_module.AlertLevel = alert_module.AlertLevel
    except Exception as e:
        pass
    
    health_monitor_spec.loader.exec_module(health_monitor_module)
    HealthMonitor = health_monitor_module.HealthMonitor
    
    # Add health_monitoring section to test_config if not present
    if 'health_monitoring' not in test_config:
        test_config['health_monitoring'] = {
            'alert_history_file': os.path.join(temp_dir, 'alerts_history.json')
        }
    
    # Create service instance
    service = HealthMonitor(
        config=test_config,
        remote_executor=remote_executor
    )
    
    yield service
    
    # Cleanup
    service.close()


@pytest.fixture(scope="function")
def test_runner(test_config, remote_executor, project_root_path, temp_dir):
    """Create TestRunner instance for testing."""
    import importlib.util
    import types
    
    automation_scripts_path = project_root_path / "automation-scripts"
    
    # Create package structure if needed
    if "automation_scripts.services" not in sys.modules:
        sys.modules["automation_scripts.services"] = types.ModuleType("automation_scripts.services")
    
    # Load test_runner
    test_runner_path = automation_scripts_path / "services" / "test_runner.py"
    test_runner_spec = importlib.util.spec_from_file_location("automation_scripts.services.test_runner", test_runner_path)
    test_runner_module = importlib.util.module_from_spec(test_runner_spec)
    sys.modules["automation_scripts.services.test_runner"] = test_runner_module
    
    # Inject dependencies
    test_runner_module.RemoteExecutor = RemoteExecutor
    test_runner_module.RemoteExecutorError = RemoteExecutorError
    
    test_runner_spec.loader.exec_module(test_runner_module)
    TestRunner = test_runner_module.TestRunner
    
    # Create service instance with temp directories
    service = TestRunner(
        config=test_config,
        remote_executor=remote_executor,
        results_dir=os.path.join(temp_dir, 'test_results'),
        history_file=os.path.join(temp_dir, 'test_history.json')
    )
    
    yield service
    
    # Cleanup
    service.close()


@pytest.fixture(scope="function")
def deployment_manager(test_config, remote_executor, project_root_path, temp_dir):
    """Create DeploymentManager instance for testing."""
    import importlib.util
    import types
    
    automation_scripts_path = project_root_path / "automation-scripts"
    
    # Create package structure if needed
    if "automation_scripts.services" not in sys.modules:
        sys.modules["automation_scripts.services"] = types.ModuleType("automation_scripts.services")
    
    # Load deployment_manager
    deployment_manager_path = automation_scripts_path / "services" / "deployment_manager.py"
    deployment_manager_spec = importlib.util.spec_from_file_location("automation_scripts.services.deployment_manager", deployment_manager_path)
    deployment_manager_module = importlib.util.module_from_spec(deployment_manager_spec)
    sys.modules["automation_scripts.services.deployment_manager"] = deployment_manager_module
    
    # Inject dependencies
    deployment_manager_module.RemoteExecutor = RemoteExecutor
    deployment_manager_module.RemoteExecutorError = RemoteExecutorError
    
    deployment_manager_spec.loader.exec_module(deployment_manager_module)
    DeploymentManager = deployment_manager_module.DeploymentManager
    
    # Create service instance with temp directories
    service = DeploymentManager(
        config=test_config,
        remote_executor=remote_executor,
        logs_dir=os.path.join(temp_dir, 'deployment_logs'),
        history_file=os.path.join(temp_dir, 'deployment_history.json')
    )
    
    yield service
    
    # Cleanup
    service.close()


@pytest.fixture(scope="function")
def hardening_manager(test_config, remote_executor, test_runner, project_root_path, temp_dir):
    """Create HardeningManager instance for testing."""
    import importlib.util
    import types
    
    automation_scripts_path = project_root_path / "automation-scripts"
    
    # Create package structure if needed
    if "automation_scripts.services" not in sys.modules:
        sys.modules["automation_scripts.services"] = types.ModuleType("automation_scripts.services")
    
    # Load hardening_manager
    hardening_manager_path = automation_scripts_path / "services" / "hardening_manager.py"
    hardening_manager_spec = importlib.util.spec_from_file_location("automation_scripts.services.hardening_manager", hardening_manager_path)
    hardening_manager_module = importlib.util.module_from_spec(hardening_manager_spec)
    sys.modules["automation_scripts.services.hardening_manager"] = hardening_manager_module
    
    # Inject dependencies
    hardening_manager_module.RemoteExecutor = RemoteExecutor
    hardening_manager_module.RemoteExecutorError = RemoteExecutorError
    
    hardening_manager_spec.loader.exec_module(hardening_manager_module)
    HardeningManager = hardening_manager_module.HardeningManager
    
    # Create service instance with temp directories
    service = HardeningManager(
        config=test_config,
        remote_executor=remote_executor,
        test_runner=test_runner,
        reports_dir=os.path.join(temp_dir, 'hardening_reports'),
        history_file=os.path.join(temp_dir, 'hardening_history.json')
    )
    
    yield service
    
    # Cleanup
    service.close()


@pytest.fixture(scope="function")
def dashboard_client(test_config, remote_executor, health_monitor, repo_sync_service, config_manager, test_runner, deployment_manager, hardening_manager, project_root_path, temp_dir):
    """Create TestClient for Dashboard API."""
    from fastapi.testclient import TestClient
    import importlib.util
    import types
    
    automation_scripts_path = project_root_path / "automation-scripts"
    
    # Create package structure if needed
    if "automation_scripts.api" not in sys.modules:
        sys.modules["automation_scripts.api"] = types.ModuleType("automation_scripts.api")
    
    # Create package structure for imports
    if "automation_scripts" not in sys.modules:
        sys.modules["automation_scripts"] = types.ModuleType("automation_scripts")
        sys.modules["automation_scripts"].__path__ = [str(automation_scripts_path)]
    if "automation_scripts.services" not in sys.modules:
        sys.modules["automation_scripts.services"] = types.ModuleType("automation_scripts.services")
        sys.modules["automation_scripts.services"].__path__ = [str(automation_scripts_path / "services")]
    if "automation_scripts.utils" not in sys.modules:
        sys.modules["automation_scripts.utils"] = types.ModuleType("automation_scripts.utils")
        sys.modules["automation_scripts.utils"].__path__ = [str(automation_scripts_path / "utils")]
    if "automation_scripts.api" not in sys.modules:
        sys.modules["automation_scripts.api"] = types.ModuleType("automation_scripts.api")
        sys.modules["automation_scripts.api"].__path__ = [str(automation_scripts_path / "api")]
    
    # Load required modules first
    # Load query_templates first (dependency for query_generator)
    query_templates_path = automation_scripts_path / "utils" / "query_templates.py"
    query_templates_spec = importlib.util.spec_from_file_location(
        "automation_scripts.utils.query_templates", query_templates_path
    )
    query_templates_module = importlib.util.module_from_spec(query_templates_spec)
    sys.modules["automation_scripts.utils.query_templates"] = query_templates_module
    query_templates_spec.loader.exec_module(query_templates_module)
    
    # Load query_generator
    query_generator_path = automation_scripts_path / "utils" / "query_generator.py"
    query_generator_spec = importlib.util.spec_from_file_location(
        "automation_scripts.utils.query_generator", query_generator_path
    )
    query_generator_module = importlib.util.module_from_spec(query_generator_spec)
    sys.modules["automation_scripts.utils.query_generator"] = query_generator_module
    query_generator_spec.loader.exec_module(query_generator_module)
    
    # Load playbook_validator (dependency for playbook_manager)
    playbook_validator_path = automation_scripts_path / "utils" / "playbook_validator.py"
    playbook_validator_spec = importlib.util.spec_from_file_location(
        "automation_scripts.utils.playbook_validator", playbook_validator_path
    )
    playbook_validator_module = importlib.util.module_from_spec(playbook_validator_spec)
    sys.modules["automation_scripts.utils.playbook_validator"] = playbook_validator_module
    playbook_validator_spec.loader.exec_module(playbook_validator_module)
    
    # Load data_package (dependency for playbook_engine and pipeline_orchestrator)
    data_package_path = automation_scripts_path / "utils" / "data_package.py"
    data_package_spec = importlib.util.spec_from_file_location(
        "automation_scripts.utils.data_package", data_package_path
    )
    data_package_module = importlib.util.module_from_spec(data_package_spec)
    sys.modules["automation_scripts.utils.data_package"] = data_package_module
    data_package_spec.loader.exec_module(data_package_module)
    # Make data_package available as attribute
    if "automation_scripts.utils" in sys.modules:
        sys.modules["automation_scripts.utils"].data_package = data_package_module
    
    # Load deterministic_anonymizer (dependency for playbook_engine and pipeline_orchestrator)
    deterministic_anonymizer_path = automation_scripts_path / "utils" / "deterministic_anonymizer.py"
    deterministic_anonymizer_spec = importlib.util.spec_from_file_location(
        "automation_scripts.utils.deterministic_anonymizer", deterministic_anonymizer_path
    )
    deterministic_anonymizer_module = importlib.util.module_from_spec(deterministic_anonymizer_spec)
    sys.modules["automation_scripts.utils.deterministic_anonymizer"] = deterministic_anonymizer_module
    deterministic_anonymizer_spec.loader.exec_module(deterministic_anonymizer_module)
    
    # Create orchestrators package structure
    if "automation_scripts.orchestrators" not in sys.modules:
        sys.modules["automation_scripts.orchestrators"] = types.ModuleType("automation_scripts.orchestrators")
        sys.modules["automation_scripts.orchestrators"].__path__ = [str(automation_scripts_path / "orchestrators")]
    
    # Load playbook_engine (dependency for pipeline_orchestrator)
    playbook_engine_path = automation_scripts_path / "orchestrators" / "playbook_engine.py"
    playbook_engine_spec = importlib.util.spec_from_file_location(
        "automation_scripts.orchestrators.playbook_engine", playbook_engine_path
    )
    playbook_engine_module = importlib.util.module_from_spec(playbook_engine_spec)
    sys.modules["automation_scripts.orchestrators.playbook_engine"] = playbook_engine_module
    playbook_engine_spec.loader.exec_module(playbook_engine_module)
    
    # Load pipeline_orchestrator (dependency for dashboard_api)
    pipeline_orchestrator_path = automation_scripts_path / "orchestrators" / "pipeline_orchestrator.py"
    pipeline_orchestrator_spec = importlib.util.spec_from_file_location(
        "automation_scripts.orchestrators.pipeline_orchestrator", pipeline_orchestrator_path
    )
    pipeline_orchestrator_module = importlib.util.module_from_spec(pipeline_orchestrator_spec)
    sys.modules["automation_scripts.orchestrators.pipeline_orchestrator"] = pipeline_orchestrator_module
    pipeline_orchestrator_spec.loader.exec_module(pipeline_orchestrator_module)
    
    # Load playbook_manager (dependency for dashboard_api)
    playbook_manager_path = automation_scripts_path / "services" / "playbook_manager.py"
    playbook_manager_spec = importlib.util.spec_from_file_location(
        "automation_scripts.services.playbook_manager", playbook_manager_path
    )
    playbook_manager_module = importlib.util.module_from_spec(playbook_manager_spec)
    sys.modules["automation_scripts.services.playbook_manager"] = playbook_manager_module
    playbook_manager_spec.loader.exec_module(playbook_manager_module)
    
    # Load dashboard_api
    dashboard_api_path = automation_scripts_path / "api" / "dashboard_api.py"
    dashboard_api_spec = importlib.util.spec_from_file_location("automation_scripts.api.dashboard_api", dashboard_api_path)
    dashboard_api_module = importlib.util.module_from_spec(dashboard_api_spec)
    sys.modules["automation_scripts.api.dashboard_api"] = dashboard_api_module
    
    # Set environment variables
    os.environ['CONFIG_PATH'] = str(project_root_path / "configs" / "config.yml")
    
    dashboard_api_spec.loader.exec_module(dashboard_api_module)
    
    # Override service getters to use test instances
    dashboard_api_module.get_health_monitor = lambda: health_monitor
    dashboard_api_module.get_repo_sync = lambda: repo_sync_service
    dashboard_api_module.get_config_manager = lambda: config_manager
    dashboard_api_module.get_remote_executor = lambda: remote_executor
    dashboard_api_module.get_test_runner = lambda: test_runner
    dashboard_api_module.get_deployment_manager = lambda: deployment_manager
    dashboard_api_module.get_hardening_manager = lambda: hardening_manager
    
    # Override get_query_generator to use test playbooks directory if provided
    # This will be set by tests that need custom playbooks
    if hasattr(dashboard_api_module, 'get_query_generator'):
        original_get_query_generator = dashboard_api_module.get_query_generator
        def get_query_generator_with_playbooks_dir(playbooks_dir=None):
            if playbooks_dir:
                # Create QueryGenerator with custom playbooks directory
                import sys
                import importlib.util
                import types
                automation_scripts_path = project_root_path / "automation-scripts"
                sys.path.insert(0, str(automation_scripts_path))
                
                if "automation_scripts.utils" not in sys.modules:
                    sys.modules["automation_scripts.utils"] = types.ModuleType("automation_scripts.utils")
                    sys.modules["automation_scripts.utils"].__path__ = [str(automation_scripts_path / "utils")]
                
                query_generator_path = automation_scripts_path / "utils" / "query_generator.py"
                spec = importlib.util.spec_from_file_location(
                    "automation_scripts.utils.query_generator", query_generator_path
                )
                query_generator_module = importlib.util.module_from_spec(spec)
                sys.modules["automation_scripts.utils.query_generator"] = query_generator_module
                spec.loader.exec_module(query_generator_module)
                
                QueryGenerator = query_generator_module.QueryGenerator
                return QueryGenerator(playbooks_dir=playbooks_dir)
            else:
                return original_get_query_generator()
        
        # Store original and custom function
        dashboard_api_module._original_get_query_generator = original_get_query_generator
        dashboard_api_module._get_query_generator_with_playbooks_dir = get_query_generator_with_playbooks_dir
    
    app = dashboard_api_module.app
    client = TestClient(app)
    
    # Store dashboard_api_module for later use
    client._dashboard_api_module = dashboard_api_module
    
    yield client


@pytest.fixture(scope="function")
def temp_playbook_dir(project_root_path):
    """
    Create a temporary playbook directory based on template for testing.
    
    Returns:
        Path: Path to temporary playbook directory
    """
    template_path = project_root_path / "playbooks" / "template"
    temp_dir = tempfile.mkdtemp(prefix="th_test_playbook_")
    temp_path = Path(temp_dir)
    
    try:
        # Copy template structure
        if template_path.exists():
            # Copy all files and directories
            for item in template_path.iterdir():
                if item.name.startswith('.'):
                    continue  # Skip hidden files
                if item.is_file():
                    shutil.copy2(item, temp_path / item.name)
                elif item.is_dir():
                    shutil.copytree(item, temp_path / item.name)
        
        # Ensure required directories exist (even if empty in template)
        required_dirs = ["queries", "scripts", "config", "tests", "examples"]
        for dir_name in required_dirs:
            dir_path = temp_path / dir_name
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
        
        yield temp_path
        
    finally:
        # Cleanup
        if temp_path.exists():
            shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture(scope="function")
def temp_playbooks_with_t1059(project_root_path):
    """
    Create temporary playbooks directory with T1059 playbook for testing.
    
    Returns:
        Path: Path to temporary playbooks directory
    """
    template_path = project_root_path / "playbooks" / "template"
    temp_dir = tempfile.mkdtemp(prefix="th_test_playbooks_")
    temp_path = Path(temp_dir)
    
    try:
        # Create T1059 playbook
        t1059_path = temp_path / "T1059-command-and-scripting-interpreter"
        t1059_path.mkdir(parents=True)
        
        # Copy template structure
        if template_path.exists():
            for item in template_path.iterdir():
                if item.name.startswith('.'):
                    continue
                if item.is_file():
                    shutil.copy2(item, t1059_path / item.name)
                elif item.is_dir():
                    shutil.copytree(item, t1059_path / item.name)
        
        # Update metadata.yml for T1059
        metadata_path = t1059_path / "metadata.yml"
        with open(metadata_path, 'r') as f:
            metadata = yaml.safe_load(f)
        
        # Update for T1059
        metadata['playbook']['id'] = "T1059-command-and-scripting-interpreter"
        metadata['playbook']['name'] = "Command and Scripting Interpreter Detection"
        metadata['mitre']['technique_id'] = "T1059"
        metadata['mitre']['technique_name'] = "Command and Scripting Interpreter"
        metadata['mitre']['tactic'] = "Execution"
        
        with open(metadata_path, 'w') as f:
            yaml.dump(metadata, f, default_flow_style=False, allow_unicode=True)
        
        yield temp_path
        
    finally:
        # Cleanup
        if temp_path.exists():
            shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture(scope="function")
def temp_playbooks_with_multiple(project_root_path):
    """
    Create temporary playbooks directory with T1059, T1047, T1071 playbooks for testing.
    
    Returns:
        Path: Path to temporary playbooks directory
    """
    template_path = project_root_path / "playbooks" / "template"
    temp_dir = tempfile.mkdtemp(prefix="th_test_playbooks_multi_")
    temp_path = Path(temp_dir)
    
    try:
        techniques = [
            ("T1059", "Command and Scripting Interpreter", "Execution"),
            ("T1047", "Windows Management Instrumentation", "Execution"),
            ("T1071", "Application Layer Protocol", "Command and Control")
        ]
        
        for technique_id, technique_name, tactic in techniques:
            playbook_path = temp_path / f"{technique_id}-{technique_name.lower().replace(' ', '-')}"
            playbook_path.mkdir(parents=True)
            
            # Copy template structure
            if template_path.exists():
                for item in template_path.iterdir():
                    if item.name.startswith('.'):
                        continue
                    if item.is_file():
                        shutil.copy2(item, playbook_path / item.name)
                    elif item.is_dir():
                        shutil.copytree(item, playbook_path / item.name)
            
            # Update metadata.yml
            metadata_path = playbook_path / "metadata.yml"
            with open(metadata_path, 'r') as f:
                metadata = yaml.safe_load(f)
            
            metadata['playbook']['id'] = f"{technique_id}-{technique_name.lower().replace(' ', '-')}"
            metadata['playbook']['name'] = f"{technique_name} Detection"
            metadata['mitre']['technique_id'] = technique_id
            metadata['mitre']['technique_name'] = technique_name
            metadata['mitre']['tactic'] = tactic
            
            with open(metadata_path, 'w') as f:
                yaml.dump(metadata, f, default_flow_style=False, allow_unicode=True)
        
        yield temp_path
        
    finally:
        # Cleanup
        if temp_path.exists():
            shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture(scope="function")
def temp_anonymizer(project_root_path):
    """
    Create a temporary DeterministicAnonymizer instance for testing.
    Uses SQLite in-memory database for testing without PostgreSQL dependency.
    """
    import sqlite3
    import tempfile
    from pathlib import Path
    
    try:
        import sys
        import importlib.util
        import types
        
        automation_scripts_path = project_root_path / "automation-scripts"
        sys.path.insert(0, str(automation_scripts_path))
        
        if "automation_scripts" not in sys.modules:
            sys.modules["automation_scripts"] = types.ModuleType("automation_scripts")
            sys.modules["automation_scripts"].__path__ = [str(automation_scripts_path)]
        if "automation_scripts.utils" not in sys.modules:
            sys.modules["automation_scripts.utils"] = types.ModuleType("automation_scripts.utils")
            sys.modules["automation_scripts.utils"].__path__ = [str(automation_scripts_path / "utils")]
        
        deterministic_anonymizer_path = automation_scripts_path / "utils" / "deterministic_anonymizer.py"
        spec = importlib.util.spec_from_file_location(
            "automation_scripts.utils.deterministic_anonymizer", deterministic_anonymizer_path
        )
        deterministic_anonymizer_module = importlib.util.module_from_spec(spec)
        sys.modules["automation_scripts.utils.deterministic_anonymizer"] = deterministic_anonymizer_module
        spec.loader.exec_module(deterministic_anonymizer_module)
        
        DeterministicAnonymizer = deterministic_anonymizer_module.DeterministicAnonymizer
        
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db_path = temp_db.name
        temp_db.close()
        
        class SQLiteConnection:
            def __init__(self, db_path):
                self.conn = sqlite3.connect(db_path, check_same_thread=False)
                self.conn.row_factory = sqlite3.Row
                self.autocommit = True
                self._db_path = db_path
                # Create table and indexes separately for SQLite
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS anonymization_mapping (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        original_hash VARCHAR(64) NOT NULL,
                        original_value TEXT,
                        anonymized_value VARCHAR(255) NOT NULL,
                        value_type VARCHAR(50) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(original_hash, value_type)
                    )
                """)
                self.conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_anonymization_mapping_hash 
                    ON anonymization_mapping(original_hash, value_type)
                """)
                self.conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_anonymization_mapping_anonymized 
                    ON anonymization_mapping(anonymized_value, value_type)
                """)
                self.conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_anonymization_mapping_type 
                    ON anonymization_mapping(value_type)
                """)
                self.conn.commit()
            
            def cursor(self, cursor_factory=None):
                # Return a cursor that supports context manager and executescript for multiple statements
                class SQLiteCursor:
                    def __init__(self, conn):
                        self.conn = conn
                        self.cursor = conn.cursor()
                    
                    def __enter__(self):
                        return self
                    
                    def __exit__(self, exc_type, exc_val, exc_tb):
                        self.cursor.close()
                        return False
                    
                    def execute(self, query, params=None):
                        # SQLite doesn't support multiple statements in one execute
                        # Split by semicolon and execute separately
                        # Also convert PostgreSQL %s to SQLite ?
                        if params is None:
                            params = ()
                        # Convert PostgreSQL %s to SQLite ?
                        query = query.replace('%s', '?')
                        # Convert SERIAL to INTEGER for SQLite
                        query = query.replace('SERIAL PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
                        # Remove PostgreSQL-specific syntax
                        query = query.replace('TIMESTAMP WITH TIME ZONE', 'TIMESTAMP')
                        statements = [s.strip() for s in query.split(';') if s.strip()]
                        for stmt in statements:
                            if stmt:
                                self.cursor.execute(stmt, params)
                        return self.cursor
                    
                    def fetchone(self):
                        return self.cursor.fetchone()
                    
                    def fetchall(self):
                        return self.cursor.fetchall()
                
                return SQLiteCursor(self.conn)
            
            def close(self):
                self.conn.close()
                try:
                    Path(self._db_path).unlink()
                except:
                    pass
        
        try:
            import psycopg2
            original_connect = psycopg2.connect
            
            def mock_connect(**kwargs):
                return SQLiteConnection(temp_db_path)
            
            psycopg2.connect = mock_connect
            import psycopg2.extras
            psycopg2.extras.RealDictCursor = sqlite3.Row
            
            anonymizer = DeterministicAnonymizer(
                db_config={'database': temp_db_path},
                use_cache=True,
                salt="test_salt_for_determinism"
            )
            
            yield anonymizer
            
            anonymizer.close()
            psycopg2.connect = original_connect
        except ImportError:
            pytest.skip("psycopg2 not available")
    except Exception as e:
        pytest.skip(f"DeterministicAnonymizer not available: {e}")


@pytest.fixture(scope="function")
def temp_anonymizer_factory(project_root_path):
    """Factory fixture for creating DeterministicAnonymizer instances with custom salt."""
    import sqlite3
    import tempfile
    from pathlib import Path
    
    def _create_anonymizer(salt=None):
        try:
            import sys
            import importlib.util
            import types
            
            automation_scripts_path = project_root_path / "automation-scripts"
            sys.path.insert(0, str(automation_scripts_path))
            
            if "automation_scripts" not in sys.modules:
                sys.modules["automation_scripts"] = types.ModuleType("automation_scripts")
                sys.modules["automation_scripts"].__path__ = [str(automation_scripts_path)]
            if "automation_scripts.utils" not in sys.modules:
                sys.modules["automation_scripts.utils"] = types.ModuleType("automation_scripts.utils")
                sys.modules["automation_scripts.utils"].__path__ = [str(automation_scripts_path / "utils")]
            
            deterministic_anonymizer_path = automation_scripts_path / "utils" / "deterministic_anonymizer.py"
            spec = importlib.util.spec_from_file_location(
                "automation_scripts.utils.deterministic_anonymizer", deterministic_anonymizer_path
            )
            deterministic_anonymizer_module = importlib.util.module_from_spec(spec)
            sys.modules["automation_scripts.utils.deterministic_anonymizer"] = deterministic_anonymizer_module
            spec.loader.exec_module(deterministic_anonymizer_module)
            
            DeterministicAnonymizer = deterministic_anonymizer_module.DeterministicAnonymizer
            
            temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
            temp_db_path = temp_db.name
            temp_db.close()
            
            class SQLiteConnection:
                def __init__(self, db_path):
                    self.conn = sqlite3.connect(db_path, check_same_thread=False)
                    self.conn.row_factory = sqlite3.Row
                    self.autocommit = True
                    self._db_path = db_path
                    # Create table and indexes separately for SQLite
                    self.conn.execute("""
                        CREATE TABLE IF NOT EXISTS anonymization_mapping (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            original_hash VARCHAR(64) NOT NULL,
                            original_value TEXT,
                            anonymized_value VARCHAR(255) NOT NULL,
                            value_type VARCHAR(50) NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(original_hash, value_type)
                        )
                    """)
                    self.conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_anonymization_mapping_hash 
                        ON anonymization_mapping(original_hash, value_type)
                    """)
                    self.conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_anonymization_mapping_anonymized 
                        ON anonymization_mapping(anonymized_value, value_type)
                    """)
                    self.conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_anonymization_mapping_type 
                        ON anonymization_mapping(value_type)
                    """)
                    self.conn.commit()
                
                def cursor(self, cursor_factory=None):
                    # Return a cursor that supports context manager and executescript for multiple statements
                    class SQLiteCursor:
                        def __init__(self, conn):
                            self.conn = conn
                            self.cursor = conn.cursor()
                        
                        def __enter__(self):
                            return self
                        
                        def __exit__(self, exc_type, exc_val, exc_tb):
                            self.cursor.close()
                            return False
                        
                        def execute(self, query, params=None):
                            # SQLite doesn't support multiple statements in one execute
                            # Split by semicolon and execute separately
                            # Also convert PostgreSQL %s to SQLite ?
                            if params is None:
                                params = ()
                            # Convert PostgreSQL %s to SQLite ?
                            query = query.replace('%s', '?')
                            # Convert SERIAL to INTEGER for SQLite
                            query = query.replace('SERIAL PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
                            # Remove PostgreSQL-specific syntax
                            query = query.replace('TIMESTAMP WITH TIME ZONE', 'TIMESTAMP')
                            statements = [s.strip() for s in query.split(';') if s.strip()]
                            for stmt in statements:
                                if stmt:
                                    self.cursor.execute(stmt, params)
                            return self.cursor
                        
                        def fetchone(self):
                            return self.cursor.fetchone()
                        
                        def fetchall(self):
                            return self.cursor.fetchall()
                    
                    return SQLiteCursor(self.conn)
                
                def close(self):
                    self.conn.close()
                    try:
                        Path(self._db_path).unlink()
                    except:
                        pass
            
            try:
                import psycopg2
                original_connect = psycopg2.connect
                
                def mock_connect(**kwargs):
                    return SQLiteConnection(temp_db_path)
                
                psycopg2.connect = mock_connect
                import psycopg2.extras
                psycopg2.extras.RealDictCursor = sqlite3.Row
                
                anonymizer = DeterministicAnonymizer(
                    db_config={'database': temp_db_path},
                    use_cache=True,
                    salt=salt or "test_salt_for_determinism"
                )
                
                return anonymizer
            except ImportError:
                pytest.skip("psycopg2 not available")
        except Exception as e:
            pytest.skip(f"DeterministicAnonymizer not available: {e}")
    
    return _create_anonymizer
