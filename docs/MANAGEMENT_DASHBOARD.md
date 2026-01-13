# Management Dashboard Documentation

## Overview

The Management Dashboard is the central control interface for the Threat Hunting Automation Lab system. It provides a unified web-based interface for monitoring system health, managing configurations, synchronizing repositories, and coordinating operations across all virtual machines.

## Access

**URL**: `http://<VM-04_IP>:5678/webhook/dashboard`

**Authentication**: Configured via n8n Basic Auth or OAuth

## Features

### 1. System Overview

The System Overview provides a real-time view of all system components and their status.

#### VM Status Cards

Each VM is displayed as a color-coded card:
- 🟢 **Green**: VM is healthy (all services running, metrics normal)
- 🟡 **Yellow**: VM is in degraded state (some services down or metrics elevated)
- 🔴 **Red**: VM is unhealthy (critical services down or metrics critical)

#### System Metrics

For each VM, the dashboard displays:
- **CPU Usage**: Current CPU utilization percentage
- **Memory Usage**: Current memory utilization percentage
- **Disk Usage**: Current disk space utilization percentage
- **Service Status**: Status of key services (PostgreSQL, JupyterLab, n8n, Docker)

#### Automatic Refresh

The dashboard automatically refreshes every 5 minutes to show current system status. Manual refresh is also available.

### 2. Health Monitoring

#### Health Check Status

- **Overall Health**: Aggregated health status across all VMs
- **Individual VM Health**: Detailed health status for each VM
- **Service Health**: Status of individual services on each VM
- **Last Check Time**: Timestamp of last health check

#### Health Check Actions

- **Manual Health Check**: Trigger immediate health check for specific VM or all VMs
- **Scheduled Health Checks**: Automatic health checks every 5 minutes
- **Health History**: View health check history and trends

### 3. Repository Synchronization

#### Sync Status

- **Repository Status**: Current Git repository status on each VM
- **Branch Information**: Current branch on each VM
- **Last Sync Time**: Timestamp of last successful synchronization
- **Sync History**: History of synchronization operations

#### Sync Actions

- **Sync to All VMs**: Synchronize repository to all VMs at once
- **Sync to Specific VM**: Synchronize repository to a specific VM
- **Sync Specific Branch**: Synchronize a specific branch to VMs
- **Verify Sync**: Verify that all VMs have the latest code

### 4. Configuration Management

#### Configuration View

- **Current Configuration**: View current system configuration
- **Configuration Validation**: Validate configuration structure and values
- **Configuration History**: View configuration change history

#### Configuration Actions

- **Edit Configuration**: Update system configuration through dashboard
- **Validate Configuration**: Validate configuration before saving
- **Backup Configuration**: Create backup before making changes
- **Restore Configuration**: Restore from previous backup

### 5. Quick Actions

Quick access to common operations:

- **Health Checks**: Run health check for selected VM
- **Connection Tests**: Test connectivity between VMs
- **Service Status**: Check status of services (PostgreSQL, JupyterLab, n8n, Docker)
- **Repository Sync**: Quick repository synchronization
- **Configuration View**: Quick access to configuration

## API Endpoints

The Management Dashboard is powered by REST API endpoints. All endpoints are available at:

**Base URL**: `http://<VM-04_IP>:8000/api`

### System Overview

#### `GET /api/system/overview`

Get system overview with status of all VMs.

**Response**:
```json
{
  "timestamp": "2025-01-12T10:00:00Z",
  "summary": {
    "total_vms": 4,
    "healthy_vms": 3,
    "degraded_vms": 1,
    "unhealthy_vms": 0
  },
  "vms": {
    "vm01": {
      "status": "healthy",
      "cpu_usage": 45.2,
      "memory_usage": 62.1,
      "disk_usage": 38.5,
      "services": {
        "postgresql": "running",
        "jupyter": "running"
      }
    }
  }
}
```

### Health Monitoring

#### `POST /api/health/check`

Check health of specific VM or all VMs.

**Request**:
```json
{
  "vm_id": "vm01"  // Optional: omit to check all VMs
}
```

**Response**:
```json
{
  "success": true,
  "vm_id": "vm01",
  "status": {
    "overall": "healthy",
    "services": {
      "postgresql": "running",
      "jupyter": "running"
    },
    "metrics": {
      "cpu": 45.2,
      "memory": 62.1,
      "disk": 38.5
    }
  },
  "execution_time": 1.23
}
```

### Repository Synchronization

#### `POST /api/repo/sync`

Synchronize repository to VMs.

**Request**:
```json
{
  "vm_id": "vm01",  // Optional: omit to sync to all VMs
  "branch": "main"  // Optional: omit to use current branch
}
```

**Response**:
```json
{
  "success": true,
  "vm_id": "vm01",
  "message": "Repository synchronized successfully",
  "execution_time": 3.45,
  "details": {
    "branch": "main",
    "commit": "abc123",
    "status": "up_to_date"
  }
}
```

### Configuration Management

#### `GET /api/config`

Get current system configuration.

**Response**:
```json
{
  "success": true,
  "config": {
    "vms": {...},
    "database": {...},
    "services": {...}
  },
  "timestamp": "2025-01-12T10:00:00Z"
}
```

#### `POST /api/config/update`

Update system configuration.

**Request**:
```json
{
  "config_data": {
    "vms": {
      "vm01": {
        "ip": "10.0.0.10"
      }
    }
  },
  "validate": true,
  "create_backup": true
}
```

**Response**:
```json
{
  "success": true,
  "message": "Configuration updated successfully",
  "validation": {
    "valid": true,
    "errors": []
  },
  "backup_name": "config_backup_20250112_100000.yml"
}
```

## Usage Examples

### Viewing System Overview

1. Open dashboard: `http://<VM-04_IP>:5678/webhook/dashboard`
2. System overview is displayed automatically
3. View VM status cards and metrics
4. Click "Refresh" for manual update

### Running Health Check

1. Click "Health Check" button
2. Select VM (or "All VMs")
3. Click "Run Health Check"
4. View results in dashboard

### Synchronizing Repository

1. Click "Sync Repository" button
2. Select target VMs (or "All VMs")
3. Optionally select branch
4. Click "Sync"
5. View sync status and results

### Updating Configuration

1. Click "Configuration" section
2. View current configuration
3. Click "Edit Configuration"
4. Make changes
5. Click "Validate" to check configuration
6. Click "Save" to apply changes (backup created automatically)

## Integration with n8n Workflows

The Management Dashboard is implemented as an n8n workflow that integrates with:

- **Health Monitor Service**: For health checks and metrics
- **Repository Sync Service**: For repository synchronization
- **Configuration Manager**: For configuration management
- **Remote Executor**: For remote command execution
- **Dashboard API**: REST API endpoints

## Dashboard Components

### Frontend

- **HTML/CSS/JavaScript**: Client-side dashboard interface
- **Real-time Updates**: Automatic refresh every 5 minutes
- **Interactive Elements**: Buttons, forms, status indicators

### Backend

- **n8n Workflows**: Workflow automation and coordination
- **REST API**: FastAPI endpoints for data access
- **Services**: Integration with all system services

## Troubleshooting

### Dashboard Not Loading

1. Check if n8n workflow is activated
2. Verify webhook URL is correct
3. Check n8n logs: `docker logs n8n`
4. Verify API is running: `curl http://<VM-04_IP>:8000/api/health`

### Health Checks Not Working

1. Check if API is running and accessible
2. Verify SSH access to VMs
3. Check authentication configuration
4. Review API logs for errors

### Repository Sync Failing

1. Verify Git repository is configured on all VMs
2. Check SSH permissions to remote VMs
3. Verify network connectivity
4. Check sync logs in n8n

### Configuration Update Failing

1. Verify configuration structure is valid
2. Check backup creation succeeded
3. Review validation errors
4. Check configuration file permissions

## Security Considerations

### Authentication

- **n8n Authentication**: Configure Basic Auth or OAuth in n8n
- **API Authentication**: Bearer token authentication for API endpoints
- **SSH Authentication**: Key-based authentication for VM access

### Access Control

- **Dashboard Access**: Restrict access to authorized users only
- **API Access**: Use API keys for programmatic access
- **Database Access**: Limit database access to necessary services only

### Data Protection

- **Configuration**: Sensitive data stored in `.env` files
- **Credentials**: Never expose credentials in dashboard
- **Audit Logging**: All operations logged for audit trail

## Best Practices

1. **Regular Health Checks**: Monitor system health regularly
2. **Configuration Backups**: Always create backups before configuration changes
3. **Repository Sync**: Keep all VMs synchronized with latest code
4. **Access Control**: Limit dashboard access to authorized personnel
5. **Monitoring**: Set up alerts for critical issues
6. **Documentation**: Document any custom configurations or changes

## Future Enhancements

- [ ] Real-time metrics with charts and graphs
- [ ] Historical data visualization
- [ ] Advanced alerting and notifications
- [ ] Custom dashboard widgets
- [ ] Role-based access control
- [ ] Audit log viewer
- [ ] Performance analytics
- [ ] Automated remediation actions

## Summary

The Management Dashboard provides a comprehensive interface for managing the Threat Hunting Automation Lab system. It integrates all major services and provides a unified view of system status, health, and configuration. The dashboard is accessible through n8n workflows and provides both web-based and API-based access to system management functions.

