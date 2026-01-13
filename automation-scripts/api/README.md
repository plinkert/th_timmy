# API Module

This directory contains REST API endpoints for the Threat Hunting Automation Lab system.

## Overview

The API module provides FastAPI-based REST endpoints that enable programmatic access to system services and integration with n8n workflows.

## Files

### `dashboard_api.py`

Main dashboard API providing endpoints for:
- System overview and health monitoring
- Repository synchronization
- Configuration management
- Testing management
- Deployment management
- Hardening management
- Playbook management
- Query generation
- Pipeline orchestration

**Key Endpoints:**
- `GET /api/system/overview` - System overview with all VM status
- `POST /api/health/check` - Health check for specific or all VMs
- `POST /api/repo/sync` - Repository synchronization
- `GET /api/config` - Get system configuration
- `POST /api/config/update` - Update system configuration
- `GET /api/playbooks` - List all playbooks
- `POST /api/playbooks/create` - Create new playbook
- `POST /api/query-generator/generate` - Generate queries for hunts

**Usage Example:**
```python
from automation_scripts.api.dashboard_api import app
import uvicorn

# Run API server
uvicorn.run(app, host="0.0.0.0", port=8000)
```

### `remote_api.py`

Remote execution API providing endpoints for:
- Remote command execution
- Remote script execution
- File upload/download operations
- SSH-based VM management

**Key Endpoints:**
- `GET /health` - API health check
- `POST /execute-command` - Execute command on remote VM
- `POST /execute-script` - Execute script on remote VM
- `POST /upload-file` - Upload file to remote VM
- `POST /download-file` - Download file from remote VM

**Usage Example:**
```python
from automation_scripts.api.remote_api import app
import uvicorn

# Run API server
uvicorn.run(app, host="0.0.0.0", port=8001)
```

## Authentication

Both APIs support optional Bearer token authentication. Configure authentication in n8n workflows or API clients:

```python
headers = {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json"
}
```

## Integration

These APIs are primarily used by:
- n8n workflows on VM-04
- Management Dashboard
- Testing Management Interface
- Deployment Management Interface
- Hardening Management Interface
- Playbook Manager Interface

## Running the APIs

### Development

```bash
# Dashboard API
cd /home/user/Desktop/TH/th_timmy
uvicorn automation-scripts.api.dashboard_api:app --host 0.0.0.0 --port 8000 --reload

# Remote API
uvicorn automation-scripts.api.remote_api:app --host 0.0.0.0 --port 8001 --reload
```

### Production

Use a process manager like systemd or supervisor to run the APIs as services.

## Dependencies

- FastAPI
- Pydantic (for request/response models)
- All services from `automation-scripts/services/`
- All utilities from `automation-scripts/utils/`

## Documentation

API documentation is available at:
- Dashboard API: `http://VM04_IP:8000/docs` (Swagger UI)
- Remote API: `http://VM04_IP:8001/docs` (Swagger UI)

