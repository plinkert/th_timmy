# Services Module

This directory contains core service modules that provide high-level functionality for system management and automation.

## Overview

Services are reusable components that encapsulate business logic and provide interfaces for common operations across the Threat Hunting Automation Lab system.

## Services

### `remote_executor.py`

**RemoteExecutor** - Remote command and script execution service.

Provides functionality for:
- Executing commands on remote VMs via SSH
- Executing scripts on remote VMs
- File upload/download operations
- Comprehensive audit logging
- Error handling and retry logic

**Usage:**
```python
from automation_scripts.services.remote_executor import RemoteExecutor

executor = RemoteExecutor(config_path="configs/config.yml")
result = executor.execute_command("vm01", "ls -la")
print(result.stdout)
```

### `ssh_client.py`

**SSHClient** - Low-level SSH client wrapper.

Provides secure SSH connections with:
- Key-based and password authentication
- Connection pooling and reuse
- Encrypted communication
- Context manager support

**Usage:**
```python
from automation_scripts.services.ssh_client import SSHClient

with SSHClient(host="10.0.0.10", username="user", key_path="~/.ssh/id_rsa") as client:
    result = client.execute("ls -la")
```

### `health_monitor.py`

**HealthMonitor** - Central health monitoring service.

Provides functionality for:
- Checking VM health status
- Collecting system metrics (CPU, RAM, disk)
- Scheduled health checks
- Alert management
- Health status aggregation

**Usage:**
```python
from automation_scripts.services.health_monitor import HealthMonitor

monitor = HealthMonitor(config_path="configs/config.yml")
status = monitor.check_vm_health("vm01")
all_status = monitor.get_health_status_all()
```

### `repo_sync.py`

**RepoSyncService** - Git repository synchronization service.

Provides functionality for:
- Synchronizing repository to single or all VMs
- Branch-specific synchronization
- Conflict detection and handling
- Sync verification
- Automatic synchronization configuration

**Usage:**
```python
from automation_scripts.services.repo_sync import RepoSyncService

sync_service = RepoSyncService(config_path="configs/config.yml")
result = sync_service.sync_repository_to_all_vms()
```

### `config_manager.py`

**ConfigManager** - Configuration management service.

Provides functionality for:
- Loading and validating configuration
- Updating configuration with validation
- Automatic backup creation
- Configuration versioning
- Configuration comparison

**Usage:**
```python
from automation_scripts.services.config_manager import ConfigManager

config_mgr = ConfigManager(config_path="configs/config.yml")
config = config_mgr.get_config()
config_mgr.update_config({"new_key": "value"}, create_backup=True)
```

### `test_runner.py`

**TestRunner** - Test execution service.

Provides functionality for:
- Running connection tests
- Running data flow tests
- Running health checks
- Test result management
- Test history tracking

**Usage:**
```python
from automation_scripts.services.test_runner import TestRunner

test_runner = TestRunner(config_path="configs/config.yml")
results = test_runner.run_connection_tests()
```

### `deployment_manager.py`

**DeploymentManager** - Deployment management service.

Provides functionality for:
- Checking installation status
- Running installations remotely
- Installation log management
- Deployment verification
- Installation rollback

**Usage:**
```python
from automation_scripts.services.deployment_manager import DeploymentManager

deploy_mgr = DeploymentManager(config_path="configs/config.yml")
status = deploy_mgr.get_installation_status("vm01")
deploy_mgr.run_installation("vm01", project_root="/home/user/th_timmy")
```

### `hardening_manager.py`

**HardeningManager** - Security hardening management service.

Provides functionality for:
- Checking hardening status
- Running security hardening
- Before/after state comparison
- Hardening report generation
- Hardening history tracking

**Usage:**
```python
from automation_scripts.services.hardening_manager import HardeningManager

hardening_mgr = HardeningManager(config_path="configs/config.yml")
status = hardening_mgr.get_hardening_status("vm01")
hardening_id = hardening_mgr.run_hardening("vm01", capture_before=True)
```

### `playbook_manager.py`

**PlaybookManager** - Playbook management service.

Provides functionality for:
- Listing all playbooks
- Creating new playbooks from template
- Editing playbook metadata
- Validating playbooks
- Testing playbooks

**Usage:**
```python
from automation_scripts.services.playbook_manager import PlaybookManager

playbook_mgr = PlaybookManager()
playbooks = playbook_mgr.list_playbooks()
playbook_mgr.create_playbook(
    playbook_id="T1566-phishing",
    technique_id="T1566",
    technique_name="Phishing",
    tactic="Initial Access"
)
```

### `metrics_collector.py`

**MetricsCollector** - System metrics collection service.

Provides functionality for:
- Collecting CPU, memory, and disk metrics
- Network metrics collection
- Service status checking
- Metrics aggregation

**Usage:**
```python
from automation_scripts.services.metrics_collector import MetricsCollector

collector = MetricsCollector(config_path="configs/config.yml")
metrics = collector.collect_metrics("vm01")
```

## Common Patterns

All services follow similar patterns:
- Configuration via `config_path` or `config` dict
- Optional logger parameter
- Comprehensive error handling with custom exceptions
- Audit logging for operations
- Integration with RemoteExecutor for VM operations

## Error Handling

All services raise custom exceptions:
- `RemoteExecutorError` - Remote execution errors
- `HealthMonitorError` - Health monitoring errors
- `RepoSyncError` - Repository sync errors
- `ConfigManagerError` - Configuration errors
- `TestRunnerError` - Test execution errors
- `DeploymentManagerError` - Deployment errors
- `HardeningManagerError` - Hardening errors
- `PlaybookManagerError` - Playbook management errors

## Dependencies

Services depend on:
- `utils/` modules for utilities
- `remote_executor.py` for VM operations
- Configuration files in `configs/`
- SSH access to VMs

## Integration

Services are used by:
- API endpoints in `api/`
- n8n workflows
- Command-line tools
- Management Dashboard

