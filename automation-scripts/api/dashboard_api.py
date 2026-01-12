"""
REST API endpoints for Management Dashboard.

This module provides FastAPI endpoints for dashboard functionality including
system overview, health monitoring, repository sync, and configuration management.
"""

import os
import json
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
from ..services.test_runner import TestRunner, TestRunnerError
from ..services.deployment_manager import DeploymentManager, DeploymentManagerError
from ..services.hardening_manager import HardeningManager, HardeningManagerError
from ..services.playbook_manager import PlaybookManager, PlaybookManagerError
from ..utils.query_generator import QueryGenerator, QueryGeneratorError


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
_test_runner: Optional[TestRunner] = None
_deployment_manager: Optional[DeploymentManager] = None
_hardening_manager: Optional[HardeningManager] = None
_query_generator: Optional[QueryGenerator] = None
_playbook_manager: Optional[PlaybookManager] = None


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


def get_test_runner() -> TestRunner:
    """Get or create TestRunner instance."""
    global _test_runner
    
    if _test_runner is None:
        config_path = os.getenv('CONFIG_PATH', 'configs/config.yml')
        remote_executor = get_remote_executor()
        results_dir = os.getenv('TEST_RESULTS_DIR', 'test_results')
        history_file = os.getenv('TEST_HISTORY_FILE', 'test_results/test_history.json')
        
        _test_runner = TestRunner(
            config_path=config_path,
            remote_executor=remote_executor,
            results_dir=results_dir,
            history_file=history_file,
            logger=logger
        )
    
    return _test_runner


def get_deployment_manager() -> DeploymentManager:
    """Get or create DeploymentManager instance."""
    global _deployment_manager
    
    if _deployment_manager is None:
        config_path = os.getenv('CONFIG_PATH', 'configs/config.yml')
        remote_executor = get_remote_executor()
        
        _deployment_manager = DeploymentManager(
            config_path=config_path,
            remote_executor=remote_executor,
            logger=logger
        )
    
    return _deployment_manager


def get_hardening_manager() -> HardeningManager:
    """Get or create HardeningManager instance."""
    global _hardening_manager
    
    if _hardening_manager is None:
        config_path = os.getenv('CONFIG_PATH', 'configs/config.yml')
        remote_executor = get_remote_executor()
        test_runner = get_test_runner()
        
        _hardening_manager = HardeningManager(
            config_path=config_path,
            remote_executor=remote_executor,
            test_runner=test_runner,
            logger=logger
        )
    
    return _hardening_manager


def get_query_generator() -> QueryGenerator:
    """Get or create QueryGenerator instance."""
    global _query_generator
    
    if _query_generator is None:
        _query_generator = QueryGenerator(logger=logger)
    
    return _query_generator


def get_playbook_manager() -> PlaybookManager:
    """Get or create PlaybookManager instance."""
    global _playbook_manager
    
    if _playbook_manager is None:
        _playbook_manager = PlaybookManager(logger=logger)
    
    return _playbook_manager


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


class ConnectionTestRequest(BaseModel):
    """Request model for connection tests."""
    vm_id: Optional[str] = Field('vm04', description="VM identifier to run tests from")


class ConnectionTestResponse(BaseModel):
    """Response model for connection tests."""
    success: bool
    test_type: str
    vm_id: str
    timestamp: str
    status: str
    passed: int
    failed: int
    warnings: int
    execution_time: float
    result_file: Optional[str] = None


class DataFlowTestRequest(BaseModel):
    """Request model for data flow tests."""
    vm_id: Optional[str] = Field('vm04', description="VM identifier to run tests from")


class DataFlowTestResponse(BaseModel):
    """Response model for data flow tests."""
    success: bool
    test_type: str
    vm_id: str
    timestamp: str
    status: str
    passed: int
    failed: int
    warnings: int
    execution_time: float
    result_file: Optional[str] = None


class TestHistoryResponse(BaseModel):
    """Response model for test history."""
    success: bool
    tests: List[Dict[str, Any]]
    total: int
    filters: Optional[Dict[str, Any]] = None


class ExportResultsRequest(BaseModel):
    """Request model for exporting test results."""
    format: str = Field('json', description="Export format: json or csv")
    test_type: Optional[str] = Field(None, description="Filter by test type")
    vm_id: Optional[str] = Field(None, description="Filter by VM ID")
    limit: Optional[int] = Field(None, description="Maximum number of results")


class ExportResultsResponse(BaseModel):
    """Response model for export results."""
    success: bool
    file_path: str
    format: str
    count: int
    message: str


@app.post("/tests/connection", response_model=ConnectionTestResponse)
async def run_connection_tests(
    request: ConnectionTestRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Run connection tests.
    
    Args:
        request: Connection test request
    
    Returns:
        Connection test result
    """
    start_time = datetime.utcnow()
    
    try:
        test_runner = get_test_runner()
        result = test_runner.run_connection_tests(vm_id=request.vm_id)
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        return ConnectionTestResponse(
            success=result.get('success', False),
            test_type=result.get('test_type', 'connections'),
            vm_id=result.get('vm_id', request.vm_id),
            timestamp=result.get('timestamp', datetime.utcnow().isoformat()),
            status=result.get('status', 'unknown'),
            passed=result.get('passed', 0),
            failed=result.get('failed', 0),
            warnings=result.get('warnings', 0),
            execution_time=execution_time,
            result_file=result.get('result_file')
        )
    except TestRunnerError as e:
        logger.error(f"Connection test error: {e}")
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


@app.post("/tests/data-flow", response_model=DataFlowTestResponse)
async def run_data_flow_tests(
    request: DataFlowTestRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Run data flow tests.
    
    Args:
        request: Data flow test request
    
    Returns:
        Data flow test result
    """
    start_time = datetime.utcnow()
    
    try:
        test_runner = get_test_runner()
        result = test_runner.run_data_flow_tests(vm_id=request.vm_id)
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        return DataFlowTestResponse(
            success=result.get('success', False),
            test_type=result.get('test_type', 'data_flow'),
            vm_id=result.get('vm_id', request.vm_id),
            timestamp=result.get('timestamp', datetime.utcnow().isoformat()),
            status=result.get('status', 'unknown'),
            passed=result.get('passed', 0),
            failed=result.get('failed', 0),
            warnings=result.get('warnings', 0),
            execution_time=execution_time,
            result_file=result.get('result_file')
        )
    except TestRunnerError as e:
        logger.error(f"Data flow test error: {e}")
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


@app.get("/tests/history", response_model=TestHistoryResponse)
async def get_test_history(
    test_type: Optional[str] = None,
    vm_id: Optional[str] = None,
    limit: Optional[int] = None,
    _: bool = Depends(verify_api_key)
):
    """
    Get test history.
    
    Args:
        test_type: Filter by test type
        vm_id: Filter by VM ID
        limit: Maximum number of results
    
    Returns:
        Test history
    """
    try:
        test_runner = get_test_runner()
        tests = test_runner.get_test_history(
            test_type=test_type,
            vm_id=vm_id,
            limit=limit
        )
        
        return TestHistoryResponse(
            success=True,
            tests=tests,
            total=len(tests),
            filters={
                'test_type': test_type,
                'vm_id': vm_id,
                'limit': limit
            } if test_type or vm_id or limit else None
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/tests/export", response_model=ExportResultsResponse)
async def export_test_results(
    request: ExportResultsRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Export test results to file.
    
    Args:
        request: Export request
    
    Returns:
        Export result
    """
    try:
        import csv
        
        # Validate format first
        format_ext = request.format.lower()
        if format_ext not in ['json', 'csv']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Format must be 'json' or 'csv'"
            )
        
        test_runner = get_test_runner()
        
        # Get test history with filters
        tests = test_runner.get_test_history(
            test_type=request.test_type,
            vm_id=request.vm_id,
            limit=request.limit
        )
        
        if not tests:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No test results found matching criteria"
            )
        
        # Generate filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        filename = f"test_results_export_{timestamp}.{format_ext}"
        export_path = test_runner.results_dir / filename
        
        # Export based on format
        if format_ext == 'json':
            with open(export_path, 'w') as f:
                json.dump({
                    'export_timestamp': datetime.utcnow().isoformat(),
                    'filters': {
                        'test_type': request.test_type,
                        'vm_id': request.vm_id,
                        'limit': request.limit
                    },
                    'count': len(tests),
                    'tests': tests
                }, f, indent=2)
        else:  # CSV
            if not tests:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No test results to export"
                )
            
            # Get all unique keys from test results
            all_keys = set()
            for test in tests:
                all_keys.update(test.keys())
            
            fieldnames = sorted(all_keys)
            
            with open(export_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for test in tests:
                    # Convert nested dicts to strings for CSV
                    row = {}
                    for key in fieldnames:
                        value = test.get(key, '')
                        if isinstance(value, (dict, list)):
                            value = json.dumps(value)
                        row[key] = value
                    writer.writerow(row)
        
        return ExportResultsResponse(
            success=True,
            file_path=str(export_path),
            format=format_ext,
            count=len(tests),
            message=f"Exported {len(tests)} test results to {filename}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


# Deployment Management Models
class InstallationStatusResponse(BaseModel):
    """Response model for installation status."""
    success: bool
    data: Dict[str, Any]
    timestamp: str


class RunInstallationRequest(BaseModel):
    """Request model for running installation."""
    vm_id: str = Field(..., description="VM identifier (e.g., 'vm01')")
    project_root: Optional[str] = Field(None, description="Project root path on VM")


class RunInstallationResponse(BaseModel):
    """Response model for installation execution."""
    success: bool
    deployment_id: str
    vm_id: str
    status: str
    message: str
    timestamp: str


class InstallationLogsResponse(BaseModel):
    """Response model for installation logs."""
    success: bool
    logs: List[Dict[str, Any]]
    total: int


class VerifyDeploymentRequest(BaseModel):
    """Request model for deployment verification."""
    vm_id: str = Field(..., description="VM identifier (e.g., 'vm01')")


class VerifyDeploymentResponse(BaseModel):
    """Response model for deployment verification."""
    success: bool
    vm_id: str
    verification_status: str
    data: Dict[str, Any]
    timestamp: str


class DeploymentSummaryResponse(BaseModel):
    """Response model for deployment summary."""
    success: bool
    summary: Dict[str, Any]
    timestamp: str


# Deployment Management Endpoints
@app.get("/deployment/installation-status", response_model=InstallationStatusResponse)
async def get_installation_status(
    vm_id: Optional[str] = None,
    _: bool = Depends(verify_api_key)
):
    """
    Get installation status for VM(s).
    
    Args:
        vm_id: Optional VM identifier (if not provided, returns status for all VMs)
    
    Returns:
        Installation status
    """
    try:
        deployment_manager = get_deployment_manager()
        
        if vm_id:
            status = deployment_manager.get_installation_status(vm_id)
            return InstallationStatusResponse(
                success=True,
                data=status,
                timestamp=datetime.utcnow().isoformat()
            )
        else:
            all_status = deployment_manager.get_installation_status_all()
            return InstallationStatusResponse(
                success=True,
                data=all_status,
                timestamp=datetime.utcnow().isoformat()
            )
            
    except DeploymentManagerError as e:
        logger.error(f"Deployment manager error: {e}")
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


@app.post("/deployment/run-installation", response_model=RunInstallationResponse)
async def run_installation(
    request: RunInstallationRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Run installation script on VM.
    
    Args:
        request: Installation request
    
    Returns:
        Installation result
    """
    try:
        deployment_manager = get_deployment_manager()
        
        result = deployment_manager.run_installation(
            vm_id=request.vm_id,
            project_root=request.project_root
        )
        
        return RunInstallationResponse(
            success=result.get('status') in ['success', 'completed'],
            deployment_id=result.get('deployment_id', ''),
            vm_id=result.get('vm_id', request.vm_id),
            status=result.get('status', 'unknown'),
            message=f"Installation {'completed' if result.get('status') == 'success' else 'failed'}",
            timestamp=result.get('timestamp', datetime.utcnow().isoformat())
        )
        
    except DeploymentManagerError as e:
        logger.error(f"Deployment manager error: {e}")
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


@app.get("/deployment/installation-logs", response_model=InstallationLogsResponse)
async def get_installation_logs(
    vm_id: Optional[str] = None,
    deployment_id: Optional[str] = None,
    limit: Optional[int] = 50,
    _: bool = Depends(verify_api_key)
):
    """
    Get installation logs.
    
    Args:
        vm_id: Optional VM identifier filter
        deployment_id: Optional deployment ID filter
        limit: Maximum number of logs to return
    
    Returns:
        Installation logs
    """
    try:
        deployment_manager = get_deployment_manager()
        
        logs = deployment_manager.get_installation_logs(
            vm_id=vm_id,
            deployment_id=deployment_id,
            limit=limit
        )
        
        return InstallationLogsResponse(
            success=True,
            logs=logs,
            total=len(logs)
        )
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/deployment/verify", response_model=VerifyDeploymentResponse)
async def verify_deployment(
    request: VerifyDeploymentRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Verify deployment on VM.
    
    Args:
        request: Verification request
    
    Returns:
        Verification result
    """
    try:
        deployment_manager = get_deployment_manager()
        
        result = deployment_manager.verify_deployment(request.vm_id)
        
        return VerifyDeploymentResponse(
            success=result.get('verification_status') == 'verified',
            vm_id=result.get('vm_id', request.vm_id),
            verification_status=result.get('verification_status', 'unknown'),
            data=result,
            timestamp=result.get('timestamp', datetime.utcnow().isoformat())
        )
        
    except DeploymentManagerError as e:
        logger.error(f"Deployment manager error: {e}")
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


@app.get("/deployment/summary", response_model=DeploymentSummaryResponse)
async def get_deployment_summary(
    _: bool = Depends(verify_api_key)
):
    """
    Get deployment summary statistics.
    
    Returns:
        Deployment summary
    """
    try:
        deployment_manager = get_deployment_manager()
        
        summary = deployment_manager.get_deployment_summary()
        
        return DeploymentSummaryResponse(
            success=True,
            summary=summary,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


# Hardening Management Models
class HardeningStatusResponse(BaseModel):
    """Response model for hardening status."""
    success: bool
    data: Dict[str, Any]
    timestamp: str


class RunHardeningRequest(BaseModel):
    """Request model for running hardening."""
    vm_id: str = Field(..., description="VM identifier (e.g., 'vm01')")
    project_root: Optional[str] = Field(None, description="Project root path on VM")
    capture_before: bool = Field(True, description="Capture system state before hardening")


class RunHardeningResponse(BaseModel):
    """Response model for hardening execution."""
    success: bool
    hardening_id: str
    vm_id: str
    status: str
    message: str
    timestamp: str


class HardeningReportsResponse(BaseModel):
    """Response model for hardening reports."""
    success: bool
    reports: List[Dict[str, Any]]
    total: int


class CompareBeforeAfterRequest(BaseModel):
    """Request model for before/after comparison."""
    hardening_id: str = Field(..., description="Hardening ID")
    vm_id: Optional[str] = Field(None, description="VM identifier (optional)")


class CompareBeforeAfterResponse(BaseModel):
    """Response model for before/after comparison."""
    success: bool
    hardening_id: str
    vm_id: str
    comparison: Dict[str, Any]
    timestamp: str


class HardeningSummaryResponse(BaseModel):
    """Response model for hardening summary."""
    success: bool
    summary: Dict[str, Any]
    timestamp: str


# Hardening Management Endpoints
@app.get("/hardening/status", response_model=HardeningStatusResponse)
async def get_hardening_status(
    vm_id: Optional[str] = None,
    _: bool = Depends(verify_api_key)
):
    """
    Get hardening status for VM(s).
    
    Args:
        vm_id: Optional VM identifier (if not provided, returns status for all VMs)
    
    Returns:
        Hardening status
    """
    try:
        hardening_manager = get_hardening_manager()
        
        if vm_id:
            status = hardening_manager.get_hardening_status(vm_id)
            return HardeningStatusResponse(
                success=True,
                data=status,
                timestamp=datetime.utcnow().isoformat()
            )
        else:
            all_status = hardening_manager.get_hardening_status_all()
            return HardeningStatusResponse(
                success=True,
                data=all_status,
                timestamp=datetime.utcnow().isoformat()
            )
            
    except HardeningManagerError as e:
        logger.error(f"Hardening manager error: {e}")
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


@app.post("/hardening/run", response_model=RunHardeningResponse)
async def run_hardening(
    request: RunHardeningRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Run hardening script on VM.
    
    Args:
        request: Hardening request
    
    Returns:
        Hardening result
    """
    try:
        hardening_manager = get_hardening_manager()
        
        result = hardening_manager.run_hardening(
            vm_id=request.vm_id,
            project_root=request.project_root,
            capture_before=request.capture_before
        )
        
        return RunHardeningResponse(
            success=result.get('status') in ['success', 'completed'],
            hardening_id=result.get('hardening_id', ''),
            vm_id=result.get('vm_id', request.vm_id),
            status=result.get('status', 'unknown'),
            message=f"Hardening {'completed' if result.get('status') == 'success' else 'failed'}",
            timestamp=result.get('timestamp', datetime.utcnow().isoformat())
        )
        
    except HardeningManagerError as e:
        logger.error(f"Hardening manager error: {e}")
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


@app.get("/hardening/reports", response_model=HardeningReportsResponse)
async def get_hardening_reports(
    vm_id: Optional[str] = None,
    hardening_id: Optional[str] = None,
    limit: Optional[int] = 50,
    _: bool = Depends(verify_api_key)
):
    """
    Get hardening reports.
    
    Args:
        vm_id: Optional VM identifier filter
        hardening_id: Optional hardening ID filter
        limit: Maximum number of reports to return
    
    Returns:
        Hardening reports
    """
    try:
        hardening_manager = get_hardening_manager()
        
        reports = hardening_manager.get_hardening_reports(
            vm_id=vm_id,
            hardening_id=hardening_id,
            limit=limit
        )
        
        return HardeningReportsResponse(
            success=True,
            reports=reports,
            total=len(reports)
        )
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/hardening/compare", response_model=CompareBeforeAfterResponse)
async def compare_before_after(
    request: CompareBeforeAfterRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Compare before/after hardening state.
    
    Args:
        request: Comparison request
    
    Returns:
        Comparison result
    """
    try:
        hardening_manager = get_hardening_manager()
        
        comparison = hardening_manager.compare_before_after(
            hardening_id=request.hardening_id,
            vm_id=request.vm_id
        )
        
        return CompareBeforeAfterResponse(
            success=True,
            hardening_id=comparison.get('hardening_id', request.hardening_id),
            vm_id=comparison.get('vm_id', request.vm_id or ''),
            comparison=comparison,
            timestamp=comparison.get('timestamp', datetime.utcnow().isoformat())
        )
        
    except HardeningManagerError as e:
        logger.error(f"Hardening manager error: {e}")
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


@app.get("/hardening/summary", response_model=HardeningSummaryResponse)
async def get_hardening_summary(
    _: bool = Depends(verify_api_key)
):
    """
    Get hardening summary statistics.
    
    Returns:
        Hardening summary
    """
    try:
        hardening_manager = get_hardening_manager()
        
        summary = hardening_manager.get_hardening_summary()
        
        return HardeningSummaryResponse(
            success=True,
            summary=summary,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


# Query Generator Models
class GenerateQueriesRequest(BaseModel):
    """Request model for query generation."""
    technique_ids: List[str] = Field(..., description="List of MITRE technique IDs (e.g., ['T1566', 'T1059'])")
    tool_names: List[str] = Field(..., description="List of tool names (e.g., ['Microsoft Defender for Endpoint', 'Splunk'])")
    mode: str = Field("manual", description="Query mode: 'manual' or 'api'")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Optional parameters (time_range, severity, etc.)")


class GenerateQueriesResponse(BaseModel):
    """Response model for query generation."""
    success: bool
    techniques: List[str]
    tools: List[str]
    mode: str
    queries: Dict[str, Any]
    warnings: List[str]
    timestamp: str


class GetPlaybooksResponse(BaseModel):
    """Response model for available playbooks."""
    success: bool
    playbooks: List[Dict[str, Any]]
    total: int
    timestamp: str


class GetAvailableToolsResponse(BaseModel):
    """Response model for available tools."""
    success: bool
    tools: List[str]
    timestamp: str


class GetQuerySummaryResponse(BaseModel):
    """Response model for query summary."""
    success: bool
    summary: Dict[str, Any]
    timestamp: str


# Query Generator Endpoints
@app.get("/query-generator/playbooks", response_model=GetPlaybooksResponse)
async def get_playbooks(
    _: bool = Depends(verify_api_key)
):
    """
    Get all available playbooks.
    
    Returns:
        List of available playbooks with MITRE techniques
    """
    try:
        query_generator = get_query_generator()
        playbooks = query_generator.discover_playbooks()
        
        return GetPlaybooksResponse(
            success=True,
            playbooks=playbooks,
            total=len(playbooks),
            timestamp=datetime.utcnow().isoformat()
        )
    except QueryGeneratorError as e:
        logger.error(f"Query generator error: {e}")
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


@app.get("/query-generator/tools", response_model=GetAvailableToolsResponse)
async def get_available_tools(
    _: bool = Depends(verify_api_key)
):
    """
    Get list of available tools from playbooks.
    
    Returns:
        List of available tool names
    """
    try:
        query_generator = get_query_generator()
        tools = query_generator.get_available_tools()
        
        return GetAvailableToolsResponse(
            success=True,
            tools=tools,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/query-generator/generate", response_model=GenerateQueriesResponse)
async def generate_queries(
    request: GenerateQueriesRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Generate queries for specified techniques and tools.
    
    Args:
        request: Query generation request
    
    Returns:
        Generated queries organized by technique and tool
    """
    try:
        query_generator = get_query_generator()
        
        result = query_generator.generate_queries(
            technique_ids=request.technique_ids,
            tool_names=request.tool_names,
            mode=request.mode,
            parameters=request.parameters
        )
        
        return GenerateQueriesResponse(
            success=True,
            techniques=result.get('techniques', []),
            tools=result.get('tools', []),
            mode=result.get('mode', request.mode),
            queries=result.get('queries', {}),
            warnings=result.get('warnings', []),
            timestamp=result.get('timestamp', datetime.utcnow().isoformat())
        )
    except QueryGeneratorError as e:
        logger.error(f"Query generator error: {e}")
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


@app.get("/query-generator/summary", response_model=GetQuerySummaryResponse)
async def get_query_summary(
    technique_ids: Optional[str] = None,
    tool_names: Optional[str] = None,
    _: bool = Depends(verify_api_key)
):
    """
    Get summary of available queries.
    
    Args:
        technique_ids: Optional comma-separated list of technique IDs
        tool_names: Optional comma-separated list of tool names
    
    Returns:
        Query summary statistics
    """
    try:
        query_generator = get_query_generator()
        
        tech_list = None
        if technique_ids:
            tech_list = [t.strip() for t in technique_ids.split(',')]
        
        tool_list = None
        if tool_names:
            tool_list = [t.strip() for t in tool_names.split(',')]
        
        summary = query_generator.get_query_summary(
            technique_ids=tech_list,
            tool_names=tool_list
        )
        
        return GetQuerySummaryResponse(
            success=True,
            summary=summary,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


# Playbook Management Models
class CreatePlaybookRequest(BaseModel):
    """Request model for creating a playbook."""
    playbook_id: str = Field(..., description="Unique playbook identifier (e.g., 'T1566-phishing')")
    technique_id: str = Field(..., description="MITRE technique ID (e.g., 'T1566')")
    technique_name: str = Field(..., description="MITRE technique name")
    tactic: str = Field(..., description="MITRE tactic name")
    author: str = Field(..., description="Playbook author")
    description: str = Field(..., description="Playbook description")
    hypothesis: str = Field(..., description="Threat hunting hypothesis")
    overwrite: bool = Field(False, description="Overwrite existing playbook")


class CreatePlaybookResponse(BaseModel):
    """Response model for playbook creation."""
    success: bool
    playbook_id: str
    path: str
    is_valid: bool
    validation_errors: List[str]
    validation_warnings: List[str]


class UpdatePlaybookRequest(BaseModel):
    """Request model for updating playbook metadata."""
    playbook_id: str = Field(..., description="Playbook ID")
    updates: Dict[str, Any] = Field(..., description="Metadata updates")


class UpdatePlaybookResponse(BaseModel):
    """Response model for playbook update."""
    success: bool
    playbook_id: str
    is_valid: bool
    validation_errors: List[str]
    validation_warnings: List[str]


class ListPlaybooksResponse(BaseModel):
    """Response model for listing playbooks."""
    success: bool
    playbooks: List[Dict[str, Any]]
    total: int
    timestamp: str


class GetPlaybookResponse(BaseModel):
    """Response model for getting a playbook."""
    success: bool
    playbook: Optional[Dict[str, Any]]
    timestamp: str


class ValidatePlaybookResponse(BaseModel):
    """Response model for playbook validation."""
    success: bool
    playbook_id: str
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    timestamp: str


class TestPlaybookResponse(BaseModel):
    """Response model for playbook testing."""
    success: bool
    playbook_id: str
    all_tests_passed: bool
    tests: Dict[str, Any]
    timestamp: str


class PlaybookSummaryResponse(BaseModel):
    """Response model for playbook summary."""
    success: bool
    summary: Dict[str, Any]
    timestamp: str


# Playbook Management Endpoints
@app.get("/playbooks/list", response_model=ListPlaybooksResponse)
async def list_playbooks(
    _: bool = Depends(verify_api_key)
):
    """
    List all available playbooks.
    
    Returns:
        List of playbooks with validation status
    """
    try:
        playbook_manager = get_playbook_manager()
        playbooks = playbook_manager.list_playbooks()
        
        return ListPlaybooksResponse(
            success=True,
            playbooks=playbooks,
            total=len(playbooks),
            timestamp=datetime.utcnow().isoformat()
        )
    except PlaybookManagerError as e:
        logger.error(f"Playbook manager error: {e}")
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


@app.get("/playbooks/{playbook_id}", response_model=GetPlaybookResponse)
async def get_playbook(
    playbook_id: str,
    _: bool = Depends(verify_api_key)
):
    """
    Get playbook by ID.
    
    Args:
        playbook_id: Playbook ID
    
    Returns:
        Playbook information
    """
    try:
        playbook_manager = get_playbook_manager()
        playbook = playbook_manager.get_playbook(playbook_id)
        
        return GetPlaybookResponse(
            success=playbook is not None,
            playbook=playbook,
            timestamp=datetime.utcnow().isoformat()
        )
    except PlaybookManagerError as e:
        logger.error(f"Playbook manager error: {e}")
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


@app.post("/playbooks/create", response_model=CreatePlaybookResponse)
async def create_playbook(
    request: CreatePlaybookRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Create a new playbook from template.
    
    Args:
        request: Playbook creation request
    
    Returns:
        Creation result with validation status
    """
    try:
        playbook_manager = get_playbook_manager()
        result = playbook_manager.create_playbook(
            playbook_id=request.playbook_id,
            technique_id=request.technique_id,
            technique_name=request.technique_name,
            tactic=request.tactic,
            author=request.author,
            description=request.description,
            hypothesis=request.hypothesis,
            overwrite=request.overwrite
        )
        
        return CreatePlaybookResponse(
            success=result['success'],
            playbook_id=result['playbook_id'],
            path=result['path'],
            is_valid=result['is_valid'],
            validation_errors=result.get('validation_errors', []),
            validation_warnings=result.get('validation_warnings', [])
        )
    except PlaybookManagerError as e:
        logger.error(f"Playbook manager error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/playbooks/update", response_model=UpdatePlaybookResponse)
async def update_playbook(
    request: UpdatePlaybookRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Update playbook metadata.
    
    Args:
        request: Playbook update request
    
    Returns:
        Update result with validation status
    """
    try:
        playbook_manager = get_playbook_manager()
        result = playbook_manager.update_playbook_metadata(
            playbook_id=request.playbook_id,
            updates=request.updates
        )
        
        return UpdatePlaybookResponse(
            success=result['success'],
            playbook_id=result['playbook_id'],
            is_valid=result['is_valid'],
            validation_errors=result.get('validation_errors', []),
            validation_warnings=result.get('validation_warnings', [])
        )
    except PlaybookManagerError as e:
        logger.error(f"Playbook manager error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/playbooks/{playbook_id}/validate", response_model=ValidatePlaybookResponse)
async def validate_playbook_endpoint(
    playbook_id: str,
    _: bool = Depends(verify_api_key)
):
    """
    Validate a playbook.
    
    Args:
        playbook_id: Playbook ID
    
    Returns:
        Validation results
    """
    try:
        playbook_manager = get_playbook_manager()
        result = playbook_manager.validate_playbook(playbook_id)
        
        return ValidatePlaybookResponse(
            success=True,
            playbook_id=result['playbook_id'],
            is_valid=result['is_valid'],
            errors=result['errors'],
            warnings=result['warnings'],
            timestamp=result['timestamp']
        )
    except PlaybookManagerError as e:
        logger.error(f"Playbook manager error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/playbooks/{playbook_id}/test", response_model=TestPlaybookResponse)
async def test_playbook_endpoint(
    playbook_id: str,
    _: bool = Depends(verify_api_key)
):
    """
    Test a playbook.
    
    Args:
        playbook_id: Playbook ID
    
    Returns:
        Test results
    """
    try:
        playbook_manager = get_playbook_manager()
        result = playbook_manager.test_playbook(playbook_id)
        
        return TestPlaybookResponse(
            success=True,
            playbook_id=result['playbook_id'],
            all_tests_passed=result['all_tests_passed'],
            tests=result['tests'],
            timestamp=result['timestamp']
        )
    except PlaybookManagerError as e:
        logger.error(f"Playbook manager error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/playbooks/summary", response_model=PlaybookSummaryResponse)
async def get_playbook_summary(
    _: bool = Depends(verify_api_key)
):
    """
    Get summary of all playbooks.
    
    Returns:
        Summary statistics
    """
    try:
        playbook_manager = get_playbook_manager()
        summary = playbook_manager.get_playbook_summary()
        
        return PlaybookSummaryResponse(
            success=True,
            summary=summary,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


# Router for inclusion in main app
router = app

