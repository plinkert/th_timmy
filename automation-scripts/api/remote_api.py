"""
REST API endpoint for remote execution service.

This module provides FastAPI endpoints for remote command execution,
script execution, and file transfer operations.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator

from ..services.remote_executor import RemoteExecutor, RemoteExecutorError


# Security
security = HTTPBearer(auto_error=False)

# Logger
logger = logging.getLogger(__name__)


# Request/Response Models
class CommandRequest(BaseModel):
    """Request model for command execution."""
    vm_id: str = Field(..., description="VM identifier (e.g., 'vm01')")
    command: str = Field(..., description="Command to execute")
    user: Optional[str] = Field(None, description="User to execute as (via sudo)")
    timeout: Optional[int] = Field(None, description="Command timeout in seconds")
    environment: Optional[Dict[str, str]] = Field(None, description="Environment variables")


class CommandResponse(BaseModel):
    """Response model for command execution."""
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    vm_id: str
    command: str
    execution_time: float


class ScriptRequest(BaseModel):
    """Request model for script execution."""
    vm_id: str = Field(..., description="VM identifier")
    script_path: str = Field(..., description="Path to script on remote VM")
    args: Optional[List[str]] = Field(None, description="Script arguments")
    user: Optional[str] = Field(None, description="User to execute as")
    timeout: Optional[int] = Field(None, description="Script timeout in seconds")
    interpreter: str = Field("/bin/bash", description="Script interpreter")


class ScriptResponse(BaseModel):
    """Response model for script execution."""
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    vm_id: str
    script_path: str
    execution_time: float


class FileUploadRequest(BaseModel):
    """Request model for file upload."""
    vm_id: str = Field(..., description="VM identifier")
    local_path: str = Field(..., description="Local file path")
    remote_path: str = Field(..., description="Remote file path")
    preserve_permissions: bool = Field(False, description="Preserve file permissions")


class FileDownloadRequest(BaseModel):
    """Request model for file download."""
    vm_id: str = Field(..., description="VM identifier")
    remote_path: str = Field(..., description="Remote file path")
    local_path: str = Field(..., description="Local file path")
    preserve_permissions: bool = Field(False, description="Preserve file permissions")


class FileOperationResponse(BaseModel):
    """Response model for file operations."""
    success: bool
    vm_id: str
    message: str
    operation_time: float


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    timestamp: str


# Global executor instance
_executor: Optional[RemoteExecutor] = None


def get_executor() -> RemoteExecutor:
    """Get or create RemoteExecutor instance."""
    global _executor
    
    if _executor is None:
        config_path = os.getenv('CONFIG_PATH', 'configs/config.yml')
        ssh_key_path = os.getenv('SSH_KEY_PATH')
        ssh_password = os.getenv('SSH_PASSWORD')
        audit_log_path = os.getenv('AUDIT_LOG_PATH', 'logs/remote_executor_audit.log')
        
        _executor = RemoteExecutor(
            config_path=config_path,
            ssh_key_path=ssh_key_path,
            ssh_password=ssh_password,
            audit_log_path=audit_log_path,
            logger=logger
        )
    
    return _executor


def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> bool:
    """
    Verify API key from Authorization header.
    
    In production, implement proper API key validation.
    For now, this is a placeholder.
    """
    api_key = os.getenv('API_KEY')
    
    if not api_key:
        # If no API key configured, allow access (development mode)
        return True
    
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
    title="Remote Execution API",
    description="REST API for remote VM command execution and file operations",
    version="1.0.0"
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="remote-execution-api",
        timestamp=datetime.utcnow().isoformat()
    )


@app.post("/execute-command", response_model=CommandResponse)
async def execute_command(
    request: CommandRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Execute command on remote VM.
    
    Args:
        request: Command execution request
    
    Returns:
        Command execution result
    """
    start_time = datetime.utcnow()
    
    try:
        executor = get_executor()
        
        exit_code, stdout, stderr = executor.execute_remote_command(
            vm_id=request.vm_id,
            command=request.command,
            user=request.user,
            timeout=request.timeout,
            environment=request.environment
        )
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        return CommandResponse(
            success=exit_code == 0,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            vm_id=request.vm_id,
            command=request.command,
            execution_time=execution_time
        )
        
    except RemoteExecutorError as e:
        logger.error(f"Remote execution error: {e}")
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


@app.post("/execute-script", response_model=ScriptResponse)
async def execute_script(
    request: ScriptRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Execute script on remote VM.
    
    Args:
        request: Script execution request
    
    Returns:
        Script execution result
    """
    start_time = datetime.utcnow()
    
    try:
        executor = get_executor()
        
        exit_code, stdout, stderr = executor.execute_remote_script(
            vm_id=request.vm_id,
            script_path=request.script_path,
            args=request.args,
            user=request.user,
            timeout=request.timeout,
            interpreter=request.interpreter
        )
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        return ScriptResponse(
            success=exit_code == 0,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            vm_id=request.vm_id,
            script_path=request.script_path,
            execution_time=execution_time
        )
        
    except RemoteExecutorError as e:
        logger.error(f"Remote execution error: {e}")
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


@app.post("/upload-file", response_model=FileOperationResponse)
async def upload_file(
    request: FileUploadRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Upload file to remote VM.
    
    Args:
        request: File upload request
    
    Returns:
        Upload operation result
    """
    start_time = datetime.utcnow()
    
    try:
        # Validate local file exists
        if not os.path.exists(request.local_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Local file not found: {request.local_path}"
            )
        
        executor = get_executor()
        
        executor.upload_file(
            vm_id=request.vm_id,
            local_path=request.local_path,
            remote_path=request.remote_path,
            preserve_permissions=request.preserve_permissions
        )
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        return FileOperationResponse(
            success=True,
            vm_id=request.vm_id,
            message=f"File uploaded successfully: {request.local_path} -> {request.remote_path}",
            operation_time=execution_time
        )
        
    except RemoteExecutorError as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/download-file", response_model=FileOperationResponse)
async def download_file(
    request: FileDownloadRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Download file from remote VM.
    
    Args:
        request: File download request
    
    Returns:
        Download operation result
    """
    start_time = datetime.utcnow()
    
    try:
        executor = get_executor()
        
        executor.download_file(
            vm_id=request.vm_id,
            remote_path=request.remote_path,
            local_path=request.local_path,
            preserve_permissions=request.preserve_permissions
        )
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        return FileOperationResponse(
            success=True,
            vm_id=request.vm_id,
            message=f"File downloaded successfully: {request.remote_path} -> {request.local_path}",
            operation_time=execution_time
        )
        
    except RemoteExecutorError as e:
        logger.error(f"Download error: {e}")
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


def create_remote_api_app(
    config_path: Optional[str] = None,
    ssh_key_path: Optional[str] = None,
    ssh_password: Optional[str] = None,
    audit_log_path: Optional[str] = None
) -> FastAPI:
    """
    Create and configure FastAPI app for remote execution API.
    
    Args:
        config_path: Path to config.yml
        ssh_key_path: Path to SSH private key
        ssh_password: SSH password (fallback)
        audit_log_path: Path to audit log file
    
    Returns:
        Configured FastAPI app
    """
    # Set environment variables for get_executor()
    if config_path:
        os.environ['CONFIG_PATH'] = config_path
    if ssh_key_path:
        os.environ['SSH_KEY_PATH'] = ssh_key_path
    if ssh_password:
        os.environ['SSH_PASSWORD'] = ssh_password
    if audit_log_path:
        os.environ['AUDIT_LOG_PATH'] = audit_log_path
    
    return app

