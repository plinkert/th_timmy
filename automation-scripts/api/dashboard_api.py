"""
REST API endpoints for Management Dashboard.

This module provides FastAPI endpoints for dashboard functionality including
system overview, health monitoring, repository sync, and configuration management.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

# Import services
import sys
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "automation-scripts"))

from ..services.health_monitor import HealthMonitor, HealthMonitorError
from ..services.repo_sync import RepoSyncService, RepoSyncError
from ..services.config_manager import ConfigManager, ConfigManagerError
from ..services.remote_executor import RemoteExecutor, RemoteExecutorError


# Security
security = HTTPBearer(auto_error=False)

# Logger
logger = logging.getLogger(__name__)


# Request/Response Models
class SystemOverviewResponse(BaseModel):
    """Response model for system overview."""
    timestamp: str
    summary: Dict[str, Any]
    vms: Dict[str, Dict[str, Any]]


class HealthCheckRequest(BaseModel):
    """Request model for health check."""
    vm_id: Optional[str] = Field(None, description="VM identifier (optional, checks all if not provided)")


class HealthCheckResponse(BaseModel):
    """Response model for health check."""
    success: bool
    vm_id: Optional[str] = None
    status: Dict[str, Any]
    execution_time: float


class RepoSyncRequest(BaseModel):
    """Request model for repository sync."""
    vm_id: Optional[str] = Field(None, description="VM identifier (optional, syncs all if not provided)")
    branch: Optional[str] = Field(None, description="Branch to sync (default: current branch)")


class RepoSyncResponse(BaseModel):
    """Response model for repository sync."""
    success: bool
    vm_id: Optional[str] = None
    message: str
    execution_time: float
    details: Optional[Dict[str, Any]] = None


class ConfigGetResponse(BaseModel):
    """Response model for getting configuration."""
    success: bool
    config: Dict[str, Any]
    timestamp: str


class ConfigUpdateRequest(BaseModel):
    """Request model for configuration update."""
    config_data: Dict[str, Any] = Field(..., description="Configuration data to update")
    validate: bool = Field(True, description="Validate configuration before saving")
    create_backup: bool = Field(True, description="Create backup before updating")


class ConfigUpdateResponse(BaseModel):
    """Response model for configuration update."""
    success: bool
    message: str
    validation: Optional[Dict[str, Any]] = None
    backup_name: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    timestamp: str


# Global service instances
_health_monitor: Optional[HealthMonitor] = None
_repo_sync: Optional[RepoSyncService] = None
_config_manager: Optional[ConfigManager] = None
_remote_executor: Optional[RemoteExecutor] = None


def get_health_monitor() -> HealthMonitor:
    """Get or create HealthMonitor instance."""
    global _health_monitor
    
    if _health_monitor is None:
        config_path = os.getenv('CONFIG_PATH', 'configs/config.yml')
        _health_monitor = HealthMonitor(config_path=config_path, logger=logger)
    
    return _health_monitor


def get_repo_sync() -> RepoSyncService:
    """Get or create RepoSyncService instance."""
    global _repo_sync
    
    if _repo_sync is None:
        config_path = os.getenv('CONFIG_PATH', 'configs/config.yml')
        remote_executor = get_remote_executor()
        _repo_sync = RepoSyncService(
            config_path=config_path,
            remote_executor=remote_executor,
            logger=logger
        )
    
    return _repo_sync


def get_config_manager() -> ConfigManager:
    """Get or create ConfigManager instance."""
    global _config_manager
    
    if _config_manager is None:
        config_path = os.getenv('CONFIG_PATH', 'configs/config.yml')
        remote_executor = get_remote_executor()
        _config_manager = ConfigManager(
            config_path=config_path,
            remote_executor=remote_executor,
            logger=logger
        )
    
    return _config_manager


def get_remote_executor() -> RemoteExecutor:
    """Get or create RemoteExecutor instance."""
    global _remote_executor
    
    if _remote_executor is None:
        config_path = os.getenv('CONFIG_PATH', 'configs/config.yml')
        ssh_key_path = os.getenv('SSH_KEY_PATH')
        ssh_password = os.getenv('SSH_PASSWORD')
        audit_log_path = os.getenv('AUDIT_LOG_PATH', 'logs/remote_executor_audit.log')
        
        _remote_executor = RemoteExecutor(
            config_path=config_path,
            ssh_key_path=ssh_key_path,
            ssh_password=ssh_password,
            audit_log_path=audit_log_path,
            logger=logger
        )
    
    return _remote_executor


def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> bool:
    """Verify API key from Authorization header."""
    api_key = os.getenv('API_KEY')
    
    if not api_key:
        return True  # Development mode
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key in Authorization header"
        )
    
    if credentials.credentials != api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return True


# FastAPI app
app = FastAPI(
    title="Management Dashboard API",
    description="REST API for Management Dashboard functionality",
    version="1.0.0"
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="dashboard-api",
        timestamp=datetime.utcnow().isoformat()
    )


@app.get("/system-overview", response_model=SystemOverviewResponse)
async def get_system_overview(
    _: bool = Depends(verify_api_key)
):
    """
    Get system overview with status of all VMs.
    
    Returns:
        System overview with VM statuses and metrics
    """
    try:
        health_monitor = get_health_monitor()
        all_status = health_monitor.get_health_status_all()
        
        return SystemOverviewResponse(
            timestamp=all_status.get('timestamp', datetime.utcnow().isoformat()),
            summary=all_status.get('summary', {}),
            vms=all_status.get('vms', {})
        )
    except Exception as e:
        logger.error(f"Failed to get system overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system overview: {str(e)}"
        )


@app.post("/health-check", response_model=HealthCheckResponse)
async def run_health_check(
    request: HealthCheckRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Run health check for VM(s).
    
    Args:
        request: Health check request
    
    Returns:
        Health check result
    """
    start_time = datetime.utcnow()
    
    try:
        health_monitor = get_health_monitor()
        
        if request.vm_id:
            # Check single VM
            health_status = health_monitor.check_vm_health(request.vm_id)
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return HealthCheckResponse(
                success=True,
                vm_id=request.vm_id,
                status=health_status,
                execution_time=execution_time
            )
        else:
            # Check all VMs
            all_status = health_monitor.get_health_status_all()
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return HealthCheckResponse(
                success=True,
                vm_id=None,
                status=all_status,
                execution_time=execution_time
            )
    except HealthMonitorError as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/sync-repository", response_model=RepoSyncResponse)
async def sync_repository(
    request: RepoSyncRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Synchronize repository to VM(s).
    
    Args:
        request: Repository sync request
    
    Returns:
        Sync operation result
    """
    start_time = datetime.utcnow()
    
    try:
        repo_sync = get_repo_sync()
        
        if request.vm_id:
            # Sync to single VM
            result = repo_sync.sync_repository_to_vm(
                vm_id=request.vm_id,
                branch=request.branch
            )
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            message = 'Sync completed' if result.get('success', False) else result.get('error', 'Sync failed')
            return RepoSyncResponse(
                success=result.get('success', False),
                vm_id=request.vm_id,
                message=message,
                execution_time=execution_time,
                details=result
            )
        else:
            # Sync to all VMs
            result = repo_sync.sync_repository_to_all_vms(branch=request.branch)
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            message = 'Sync completed' if result.get('success', False) else result.get('error', 'Sync failed')
            if 'summary' in result:
                summary = result.get('summary', {})
                message = f"Synced {summary.get('successful', 0)}/{summary.get('total', 0)} VMs"
            
            return RepoSyncResponse(
                success=result.get('success', False),
                vm_id=None,
                message=message,
                execution_time=execution_time,
                details=result
            )
    except RepoSyncError as e:
        logger.error(f"Repository sync error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/config", response_model=ConfigGetResponse)
async def get_config(
    _: bool = Depends(verify_api_key)
):
    """
    Get current configuration.
    
    Returns:
        Current configuration
    """
    try:
        config_manager = get_config_manager()
        # Get config from manager (it has self.config)
        config = config_manager.config if hasattr(config_manager, 'config') else config_manager.get_config()
        
        return ConfigGetResponse(
            success=True,
            config=config,
            timestamp=datetime.utcnow().isoformat()
        )
    except ConfigManagerError as e:
        logger.error(f"Config get error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/config", response_model=ConfigUpdateResponse)
async def update_config(
    request: ConfigUpdateRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Update configuration.
    
    Args:
        request: Configuration update request
    
    Returns:
        Update operation result
    """
    try:
        config_manager = get_config_manager()
        
        # Validate if requested
        validation = None
        if request.validate:
            validation = config_manager.validate_config(
                config_data=request.config_data,
                config_type='central'
            )
            
            if not validation.get('valid', False):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Configuration validation failed: {validation.get('errors', [])}"
                )
        
        # Update configuration
        result = config_manager.update_config(
            config_data=request.config_data,
            validate=False,  # Already validated
            create_backup=request.create_backup
        )
        
        return ConfigUpdateResponse(
            success=result.get('success', False),
            message=result.get('message', 'Configuration updated'),
            validation=validation,
            backup_name=result.get('backup_name')
        )
    except HTTPException:
        raise
    except ConfigManagerError as e:
        logger.error(f"Config update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


# Router for inclusion in main app
router = app

