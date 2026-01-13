# Remote Management Guide

## Overview

This guide explains how to remotely manage the Threat Hunting Automation Lab system. Remote management allows you to control and monitor all VMs from a central location (VM-04) without needing direct access to each machine.

## What is Remote Management?

Remote Management enables you to:

- **Execute Commands**: Run commands on remote VMs via SSH
- **Transfer Files**: Upload and download files to/from remote VMs
- **Monitor Health**: Check system health and metrics remotely
- **Manage Configuration**: Update configurations across all VMs
- **Synchronize Code**: Keep code synchronized across all VMs
- **Deploy Updates**: Deploy updates and installations remotely

## Access Methods

### Management Dashboard (Recommended)

The easiest way to manage the system remotely is through the Management Dashboard.

**Access**: `http://<VM-04_IP>:5678/webhook/dashboard`

**Features:**
- Visual interface for all operations
- Real-time system status
- One-click operations
- No command-line knowledge required

### API Endpoints

For programmatic access or automation:

**Base URL**: `http://<VM-04_IP>:8000/api`

**Authentication**: Bearer token (if configured)

### Command Line (Advanced)

For advanced users, you can use the Remote Executor service directly:

```python
from automation_scripts.services.remote_executor import RemoteExecutor

executor = RemoteExecutor(config_path='configs/config.yml')
result = executor.execute_command('vm01', 'ls -la')
```

## Remote Operations

### Health Monitoring

#### Check Single VM Health

**Via Dashboard:**
1. Open Management Dashboard
2. Click on VM card
3. Click "Run Health Check"
4. Review results

**Via API:**
```bash
curl -X POST http://<VM-04_IP>:8000/api/health/check \
  -H "Content-Type: application/json" \
  -d '{"vm_id": "vm01"}'
```

**Via Command Line:**
```python
from automation_scripts.services.health_monitor import HealthMonitor

monitor = HealthMonitor(config_path='configs/config.yml')
status = monitor.check_vm_health('vm01')
print(status)
```

#### Check All VMs Health

**Via Dashboard:**
1. Open Management Dashboard
2. Click "Refresh Status" (checks all VMs)
3. Review all VM statuses

**Via API:**
```bash
curl -X POST http://<VM-04_IP>:8000/api/health/check \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Command Execution

#### Execute Command on Remote VM

**Via API:**
```bash
curl -X POST http://<VM-04_IP>:8001/execute-command \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "vm_id": "vm01",
    "command": "df -h",
    "timeout": 30
  }'
```

**Via Python:**
```python
from automation_scripts.services.remote_executor import RemoteExecutor

executor = RemoteExecutor(config_path='configs/config.yml')
result = executor.execute_command(
    vm_id='vm01',
    command='df -h',
    timeout=30
)
print(result.stdout)
```

#### Execute Script on Remote VM

**Via API:**
```bash
curl -X POST http://<VM-04_IP>:8001/execute-script \
  -H "Content-Type: application/json" \
  -d '{
    "vm_id": "vm01",
    "script_path": "/home/user/script.sh",
    "arguments": ["arg1", "arg2"]
  }'
```

**Via Python:**
```python
result = executor.execute_script(
    vm_id='vm01',
    script_path='/home/user/script.sh',
    arguments=['arg1', 'arg2']
)
```

### File Operations

#### Upload File to Remote VM

**Via API:**
```bash
curl -X POST http://<VM-04_IP>:8001/upload-file \
  -H "Content-Type: multipart/form-data" \
  -F "vm_id=vm01" \
  -F "remote_path=/home/user/file.txt" \
  -F "file=@local_file.txt"
```

**Via Python:**
```python
result = executor.upload_file(
    vm_id='vm01',
    local_path='/local/path/file.txt',
    remote_path='/home/user/file.txt'
)
```

#### Download File from Remote VM

**Via API:**
```bash
curl -X POST http://<VM-04_IP>:8001/download-file \
  -H "Content-Type: application/json" \
  -d '{
    "vm_id": "vm01",
    "remote_path": "/home/user/file.txt",
    "local_path": "/local/path/file.txt"
  }'
```

**Via Python:**
```python
result = executor.download_file(
    vm_id='vm01',
    remote_path='/home/user/file.txt',
    local_path='/local/path/file.txt'
)
```

### Repository Synchronization

#### Sync Repository to All VMs

**Via Dashboard:**
1. Open Management Dashboard
2. Click "Sync Repository" button
3. Wait for completion
4. Review sync status

**Via API:**
```bash
curl -X POST http://<VM-04_IP>:8000/api/repo/sync \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Via Python:**
```python
from automation_scripts.services.repo_sync import RepoSyncService

sync_service = RepoSyncService(config_path='configs/config.yml')
result = sync_service.sync_repository_to_all_vms()
```

#### Sync Repository to Specific VM

**Via API:**
```bash
curl -X POST http://<VM-04_IP>:8000/api/repo/sync \
  -H "Content-Type: application/json" \
  -d '{"vm_id": "vm01"}'
```

#### Sync Specific Branch

**Via API:**
```bash
curl -X POST http://<VM-04_IP>:8000/api/repo/sync \
  -H "Content-Type: application/json" \
  -d '{
    "vm_id": "vm01",
    "branch": "develop"
  }'
```

### Configuration Management

#### Get Current Configuration

**Via Dashboard:**
1. Open Management Dashboard
2. Click "Configuration" section
3. View current configuration

**Via API:**
```bash
curl http://<VM-04_IP>:8000/api/config
```

**Via Python:**
```python
from automation_scripts.services.config_manager import ConfigManager

config_mgr = ConfigManager(config_path='configs/config.yml')
config = config_mgr.get_config()
```

#### Update Configuration

**Via Dashboard:**
1. Open Management Dashboard
2. Click "Configuration" section
3. Click "Edit Configuration"
4. Make changes
5. Click "Validate" to check
6. Click "Save" to apply

**Via API:**
```bash
curl -X POST http://<VM-04_IP>:8000/api/config/update \
  -H "Content-Type: application/json" \
  -d '{
    "config_data": {
      "vms": {
        "vm01": {
          "ip": "10.0.0.10"
        }
      }
    },
    "validate": true,
    "create_backup": true
  }'
```

**Via Python:**
```python
config_mgr.update_config(
    config_data={'vms': {'vm01': {'ip': '10.0.0.10'}}},
    validate=True,
    create_backup=True
)
```

## Common Remote Management Tasks

### Daily Operations

#### Morning System Check

1. **Open Management Dashboard**
2. **Check All VM Status**
   - Verify all VMs are healthy (green)
   - Check metrics (CPU, memory, disk)
   - Review service status
3. **Review Health Checks**
   - Check last health check time
   - Review any warnings or errors
4. **Verify Repository Sync**
   - Check last sync time
   - Verify all VMs are up to date

#### System Maintenance

1. **Update Configuration**
   - Make configuration changes
   - Validate before saving
   - Backup created automatically
2. **Sync Repository**
   - Sync latest code to all VMs
   - Verify sync completed successfully
3. **Run Health Checks**
   - Check health after changes
   - Verify services are running
4. **Review Logs**
   - Check for errors or warnings
   - Review audit logs

### Troubleshooting Remotely

#### VM Not Responding

1. **Check Health Status**
   - Use Management Dashboard
   - Review health check results
   - Check service status

2. **Test Connectivity**
   - Use Testing Management Interface
   - Run connection tests
   - Check network connectivity

3. **Review Logs**
   - Access logs remotely via SSH
   - Check system logs
   - Review application logs

4. **Restart Services**
   - Execute restart commands remotely
   - Monitor service startup
   - Verify services are running

#### Service Issues

1. **Check Service Status**
   - Use Management Dashboard
   - Review service status for each VM
   - Check service logs

2. **Restart Service**
   ```bash
   # Via API
   curl -X POST http://<VM-04_IP>:8001/execute-command \
     -H "Content-Type: application/json" \
     -d '{
       "vm_id": "vm02",
       "command": "sudo systemctl restart postgresql"
     }'
   ```

3. **Verify Service**
   - Check service status again
   - Test service functionality
   - Review logs for errors

## Security Considerations

### SSH Authentication

**Recommended**: Use SSH key-based authentication

1. **Generate SSH Key** (if not exists):
   ```bash
   ssh-keygen -t ed25519 -C "threat-hunting-lab"
   ```

2. **Copy Key to VMs**:
   ```bash
   ssh-copy-id user@vm01_ip
   ssh-copy-id user@vm02_ip
   ssh-copy-id user@vm03_ip
   ```

3. **Configure in System**:
   - Set `SSH_KEY_PATH` environment variable
   - Or configure in `configs/config.yml`

### API Authentication

**Bearer Token Authentication**:

1. **Generate API Key**
2. **Configure in System**
3. **Use in Requests**:
   ```bash
   curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://<VM-04_IP>:8000/api/system/overview
   ```

### Access Control

1. **Limit Access**: Restrict who can access management interfaces
2. **Use Strong Passwords**: For n8n and API authentication
3. **Rotate Credentials**: Regularly rotate passwords and keys
4. **Audit Access**: Monitor who accesses the system

## Best Practices

### Remote Operations

1. **Use Dashboard When Possible**: Easier and safer than command line
2. **Verify Before Execute**: Always review commands before execution
3. **Test Changes**: Test changes on single VM before applying to all
4. **Document Changes**: Document all remote operations
5. **Monitor Results**: Always check operation results

### Error Handling

1. **Check Return Codes**: Verify operations succeeded
2. **Review Error Messages**: Understand what went wrong
3. **Check Logs**: Review logs for detailed error information
4. **Retry if Appropriate**: Some operations can be retried
5. **Escalate if Needed**: Contact administrator for critical issues

### Performance

1. **Batch Operations**: Group related operations together
2. **Parallel Execution**: Execute operations in parallel when possible
3. **Monitor Timeouts**: Set appropriate timeouts for operations
4. **Optimize Commands**: Use efficient commands and scripts

## Troubleshooting

### Cannot Connect to VM

**Problem**: Remote operations fail with connection errors.

**Solutions:**
- Check network connectivity: `ping <VM_IP>`
- Verify SSH access: `ssh user@<VM_IP>`
- Check firewall rules
- Verify SSH key is configured correctly
- Check VM is running and accessible

### Authentication Failures

**Problem**: Authentication fails for remote operations.

**Solutions:**
- Verify SSH key permissions: `chmod 600 ~/.ssh/id_rsa`
- Check SSH key is added to VM: `ssh-copy-id user@<VM_IP>`
- Verify username in configuration matches VM user
- Check password if using password authentication
- Review SSH configuration on VM

### Command Execution Timeouts

**Problem**: Commands timeout before completion.

**Solutions:**
- Increase timeout value
- Check if command is actually running
- Review command complexity
- Break complex commands into smaller steps
- Check VM performance (CPU, memory)

### File Transfer Failures

**Problem**: File upload/download fails.

**Solutions:**
- Check file permissions on remote VM
- Verify disk space on remote VM
- Check network connectivity
- Verify file paths are correct
- Review file size limits

## Advanced Usage

### Scripted Operations

Create scripts for common operations:

```python
#!/usr/bin/env python3
"""Script to check all VMs and sync repository."""

from automation_scripts.services.health_monitor import HealthMonitor
from automation_scripts.services.repo_sync import RepoSyncService

# Check health
monitor = HealthMonitor(config_path='configs/config.yml')
status = monitor.get_health_status_all()
print(f"Health Status: {status}")

# Sync repository
sync_service = RepoSyncService(config_path='configs/config.yml')
result = sync_service.sync_repository_to_all_vms()
print(f"Sync Result: {result}")
```

### Automated Monitoring

Set up automated monitoring:

```python
import time
from automation_scripts.services.health_monitor import HealthMonitor

monitor = HealthMonitor(config_path='configs/config.yml')

while True:
    status = monitor.get_health_status_all()
    # Check for issues
    for vm_id, vm_status in status.items():
        if vm_status['overall'] != 'healthy':
            print(f"Alert: {vm_id} is not healthy!")
    time.sleep(300)  # Check every 5 minutes
```

## Integration with n8n Workflows

Remote management is integrated into n8n workflows:

- **Management Dashboard**: Uses remote execution for all operations
- **Testing Management**: Uses remote execution for test execution
- **Deployment Management**: Uses remote execution for deployments
- **Hardening Management**: Uses remote execution for hardening

## Summary

Remote Management enables centralized control of the entire Threat Hunting Automation Lab system. Key capabilities:

- **Centralized Control**: Manage all VMs from one location
- **Multiple Access Methods**: Dashboard, API, or command line
- **Comprehensive Operations**: Health checks, commands, file transfer, sync
- **Security**: SSH key authentication and API tokens
- **Automation**: Integrate with workflows and scripts

**Key Takeaways:**
- Use Management Dashboard for most operations
- API provides programmatic access
- Always verify operations succeeded
- Monitor system health regularly
- Follow security best practices

**Next Steps:**
- Familiarize yourself with Management Dashboard
- Practice common remote operations
- Set up automated monitoring
- Create scripts for repetitive tasks

