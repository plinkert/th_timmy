"""
Deployment Manager Service - Remote deployment management.

This module provides functionality for managing deployments remotely,
including installation, verification, and deployment history tracking.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import yaml

from .remote_executor import RemoteExecutor, RemoteExecutorError


class DeploymentManagerError(Exception):
    """Base exception for deployment manager errors."""
    pass


class DeploymentManager:
    """
    Deployment management service.
    
    Provides functionality for:
    - Running installation scripts remotely
    - Tracking installation status
    - Managing installation logs
    - Verifying deployments
    - Maintaining deployment history
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        remote_executor: Optional[RemoteExecutor] = None,
        logs_dir: Optional[str] = None,
        history_file: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Deployment Manager.
        
        Args:
            config_path: Path to config.yml file
            config: Configuration dict (alternative to config_path)
            remote_executor: Optional RemoteExecutor instance
            logs_dir: Directory for deployment logs
            history_file: Path to deployment history file
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Load configuration
        if config:
            self.config = config
        elif config_path:
            self.config = self._load_config(config_path)
        else:
            # Try default config path
            default_config = Path(__file__).parent.parent.parent / "configs" / "config.yml"
            if default_config.exists():
                self.config = self._load_config(str(default_config))
            else:
                raise DeploymentManagerError(
                    "No configuration provided. Specify config_path or config parameter."
                )
        
        # Initialize remote executor
        if remote_executor:
            self.remote_executor = remote_executor
        else:
            self.remote_executor = RemoteExecutor(
                config=self.config,
                logger=self.logger
            )
        
        # Setup directories
        if logs_dir:
            self.logs_dir = Path(logs_dir)
        else:
            project_root = Path(__file__).parent.parent.parent
            self.logs_dir = project_root / "logs" / "deployments"
        
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Deployment history
        if history_file:
            self.history_file = Path(history_file)
        else:
            project_root = Path(__file__).parent.parent.parent
            self.history_file = project_root / "logs" / "deployments" / "deployment_history.json"
        
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_history_file()
        
        # Installation script paths
        project_root = Path(__file__).parent.parent.parent
        self.install_scripts = {
            'vm01': 'hosts/vm01-ingest/install_vm01.sh',
            'vm02': 'hosts/vm02-database/install_vm02.sh',
            'vm03': 'hosts/vm03-analysis/install_vm03.sh',
            'vm04': 'hosts/vm04-orchestrator/install_vm04.sh'
        }
        
        # Determine project root on VMs
        self.vm_project_root = self.config.get('repository', {}).get('vm_repo_paths', {}).get(
            'vm01',
            '/home/thadmin/th_timmy'
        )
        
        self.logger.info("DeploymentManager initialized")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            self.logger.debug(f"Configuration loaded from {config_path}")
            return config
        except Exception as e:
            raise DeploymentManagerError(f"Failed to load configuration from {config_path}: {e}")
    
    def _ensure_history_file(self) -> None:
        """Ensure deployment history file exists."""
        if not self.history_file.exists():
            with open(self.history_file, 'w') as f:
                json.dump({'deployments': []}, f, indent=2)
    
    def _add_to_history(self, deployment_record: Dict[str, Any]) -> None:
        """Add deployment record to history."""
        try:
            # Load existing history
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
            else:
                history = {'deployments': []}
            
            # Add new deployment record
            history['deployments'].append(deployment_record)
            
            # Keep only last 500 deployment records
            if len(history['deployments']) > 500:
                history['deployments'] = history['deployments'][-500:]
            
            # Save history
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            self.logger.warning(f"Failed to add deployment to history: {e}")
    
    def _save_deployment_log(
        self,
        vm_id: str,
        log_content: str,
        deployment_id: str
    ) -> str:
        """
        Save deployment log to file.
        
        Args:
            vm_id: VM identifier
            log_content: Log content
            deployment_id: Deployment ID
        
        Returns:
            Path to saved log file
        """
        try:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"deployment_{vm_id}_{deployment_id}_{timestamp}.log"
            log_path = self.logs_dir / filename
            
            with open(log_path, 'w') as f:
                f.write(log_content)
            
            return str(log_path)
            
        except Exception as e:
            self.logger.error(f"Failed to save deployment log: {e}")
            return ""
    
    def _parse_installation_output(
        self,
        stdout: str,
        stderr: str,
        exit_code: int
    ) -> Dict[str, Any]:
        """
        Parse installation script output.
        
        Args:
            stdout: Standard output from installation
            stderr: Standard error from installation
            exit_code: Exit code from installation
        
        Returns:
            Dictionary with parsed installation results
        """
        result = {
            'exit_code': exit_code,
            'success': exit_code == 0,
            'stdout': stdout,
            'stderr': stderr,
            'installed_components': [],
            'warnings': [],
            'errors': []
        }
        
        # Try to extract information from output
        output_lines = stdout.split('\n')
        for line in output_lines:
            # Look for installed components
            if '[INFO]' in line or 'Installing' in line or 'installed' in line.lower():
                if 'Installing' in line or 'installed' in line.lower():
                    result['installed_components'].append(line.strip())
            # Look for warnings
            if '[WARN]' in line or 'WARNING' in line.upper():
                result['warnings'].append(line.strip())
            # Look for errors
            if '[ERROR]' in line or 'ERROR' in line.upper():
                result['errors'].append(line.strip())
        
        # Also check stderr for errors
        if stderr:
            stderr_lines = stderr.split('\n')
            for line in stderr_lines:
                if line.strip() and ('error' in line.lower() or 'failed' in line.lower()):
                    result['errors'].append(line.strip())
        
        return result
    
    def get_installation_status(self, vm_id: str) -> Dict[str, Any]:
        """
        Get installation status for VM.
        
        Args:
            vm_id: VM identifier
        
        Returns:
            Dictionary with installation status
        """
        try:
            self.logger.info(f"Checking installation status for {vm_id}")
            
            # Check if key components are installed
            status_checks = {
                'python3': False,
                'git': False,
                'project_directory': False,
                'venv': False
            }
            
            # Check Python
            try:
                exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                    vm_id=vm_id,
                    command="python3 --version 2>&1",
                    timeout=10
                )
                if exit_code == 0:
                    status_checks['python3'] = True
            except Exception:
                pass
            
            # Check Git
            try:
                exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                    vm_id=vm_id,
                    command="git --version 2>&1",
                    timeout=10
                )
                if exit_code == 0:
                    status_checks['git'] = True
            except Exception:
                pass
            
            # Check project directory
            try:
                exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                    vm_id=vm_id,
                    command=f"test -d {self.vm_project_root} && echo 'exists' || echo 'not_found'",
                    timeout=10
                )
                if 'exists' in stdout:
                    status_checks['project_directory'] = True
            except Exception:
                pass
            
            # Check virtual environment
            try:
                exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                    vm_id=vm_id,
                    command=f"test -d {self.vm_project_root}/venv && echo 'exists' || echo 'not_found'",
                    timeout=10
                )
                if 'exists' in stdout:
                    status_checks['venv'] = True
            except Exception:
                pass
            
            # Determine overall status
            installed_count = sum(1 for v in status_checks.values() if v)
            total_checks = len(status_checks)
            
            if installed_count == total_checks:
                overall_status = 'installed'
            elif installed_count > 0:
                overall_status = 'partial'
            else:
                overall_status = 'not_installed'
            
            return {
                'vm_id': vm_id,
                'status': overall_status,
                'checks': status_checks,
                'installed_count': installed_count,
                'total_checks': total_checks,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except RemoteExecutorError as e:
            return {
                'vm_id': vm_id,
                'status': 'unknown',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Failed to get installation status for {vm_id}: {e}")
            return {
                'vm_id': vm_id,
                'status': 'unknown',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_installation_status_all(self) -> Dict[str, Any]:
        """
        Get installation status for all enabled VMs.
        
        Returns:
            Dictionary with installation status for all VMs
        """
        try:
            vms = self.config.get('vms', {})
            enabled_vms = [
                vm_id for vm_id, vm_config in vms.items()
                if vm_config.get('enabled', True)
            ]
            
            results = {}
            installed_count = 0
            partial_count = 0
            not_installed_count = 0
            
            for vm_id in enabled_vms:
                status = self.get_installation_status(vm_id)
                results[vm_id] = status
                
                status_value = status.get('status', 'unknown')
                if status_value == 'installed':
                    installed_count += 1
                elif status_value == 'partial':
                    partial_count += 1
                else:
                    not_installed_count += 1
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'summary': {
                    'total': len(enabled_vms),
                    'installed': installed_count,
                    'partial': partial_count,
                    'not_installed': not_installed_count
                },
                'vms': results
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get installation status for all VMs: {e}")
            raise DeploymentManagerError(f"Failed to get installation status: {e}")
    
    def run_installation(
        self,
        vm_id: str,
        project_root: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run installation script on VM.
        
        Args:
            vm_id: VM identifier
            project_root: Project root path on VM (default: from config)
        
        Returns:
            Dictionary with installation results
        """
        try:
            self.logger.info(f"Starting installation on {vm_id}")
            
            if vm_id not in self.install_scripts:
                raise DeploymentManagerError(f"No installation script for {vm_id}")
            
            install_script = self.install_scripts[vm_id]
            
            if not project_root:
                project_root = self.vm_project_root
            
            # Generate deployment ID
            deployment_id = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            
            # Execute installation script with sudo
            # Note: Installation scripts require root privileges
            command = f"cd {project_root} && sudo bash {install_script} {project_root} 2>&1"
            
            self.logger.info(f"Executing installation command on {vm_id}")
            
            exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                vm_id=vm_id,
                command=command,
                timeout=1800  # Installation can take up to 30 minutes
            )
            
            # Parse output
            parsed_result = self._parse_installation_output(stdout, stderr, exit_code)
            
            # Save log
            log_content = f"=== Installation Log for {vm_id} ===\n"
            log_content += f"Deployment ID: {deployment_id}\n"
            log_content += f"Timestamp: {datetime.utcnow().isoformat()}\n"
            log_content += f"Exit Code: {exit_code}\n\n"
            log_content += "=== STDOUT ===\n"
            log_content += stdout
            log_content += "\n\n=== STDERR ===\n"
            log_content += stderr
            
            log_path = self._save_deployment_log(vm_id, log_content, deployment_id)
            
            # Create deployment record
            deployment_record = {
                'deployment_id': deployment_id,
                'vm_id': vm_id,
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'success' if exit_code == 0 else 'failed',
                'exit_code': exit_code,
                'log_file': log_path,
                'installed_components': parsed_result.get('installed_components', []),
                'warnings': parsed_result.get('warnings', []),
                'errors': parsed_result.get('errors', [])
            }
            
            # Add to history
            self._add_to_history(deployment_record)
            
            self.logger.info(
                f"Installation on {vm_id} completed: "
                f"status={deployment_record['status']}, "
                f"exit_code={exit_code}"
            )
            
            return deployment_record
            
        except RemoteExecutorError as e:
            error_record = {
                'deployment_id': datetime.utcnow().strftime('%Y%m%d_%H%M%S'),
                'vm_id': vm_id,
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'error',
                'error': str(e)
            }
            self._add_to_history(error_record)
            raise DeploymentManagerError(f"Failed to run installation on {vm_id}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error running installation on {vm_id}: {e}")
            raise DeploymentManagerError(f"Unexpected error: {e}")
    
    def verify_deployment(self, vm_id: str) -> Dict[str, Any]:
        """
        Verify deployment on VM.
        
        Args:
            vm_id: VM identifier
        
        Returns:
            Dictionary with verification results
        """
        try:
            self.logger.info(f"Verifying deployment on {vm_id}")
            
            # Get installation status
            status = self.get_installation_status(vm_id)
            
            # Run health check to verify installation
            health_check_script = f"hosts/{vm_id}/health_check.sh"
            project_root = self.vm_project_root
            
            try:
                exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                    vm_id=vm_id,
                    command=f"cd {project_root} && bash {health_check_script} {project_root} 2>&1",
                    timeout=180
                )
                
                # Parse health check results
                passed = 0
                failed = 0
                warnings = 0
                
                for line in stdout.split('\n'):
                    if 'Passed:' in line or 'passed:' in line:
                        try:
                            parts = line.split()
                            for i, part in enumerate(parts):
                                if 'passed' in part.lower():
                                    if i + 1 < len(parts):
                                        passed = int(parts[i + 1])
                        except (ValueError, IndexError):
                            pass
                    elif 'Failed:' in line or 'failed:' in line:
                        try:
                            parts = line.split()
                            for i, part in enumerate(parts):
                                if 'failed' in part.lower():
                                    if i + 1 < len(parts):
                                        failed = int(parts[i + 1])
                        except (ValueError, IndexError):
                            pass
                    elif 'Warnings:' in line or 'warnings:' in line:
                        try:
                            parts = line.split()
                            for i, part in enumerate(parts):
                                if 'warn' in part.lower():
                                    if i + 1 < len(parts):
                                        warnings = int(parts[i + 1])
                        except (ValueError, IndexError):
                            pass
                
                verification_status = 'verified' if exit_code == 0 and failed == 0 else 'failed'
                
            except Exception as e:
                self.logger.warning(f"Health check failed during verification: {e}")
                verification_status = 'unknown'
                passed = 0
                failed = 0
                warnings = 0
            
            verification_result = {
                'vm_id': vm_id,
                'timestamp': datetime.utcnow().isoformat(),
                'verification_status': verification_status,
                'installation_status': status,
                'health_check': {
                    'passed': passed,
                    'failed': failed,
                    'warnings': warnings
                }
            }
            
            return verification_result
            
        except Exception as e:
            self.logger.error(f"Failed to verify deployment on {vm_id}: {e}")
            return {
                'vm_id': vm_id,
                'timestamp': datetime.utcnow().isoformat(),
                'verification_status': 'error',
                'error': str(e)
            }
    
    def get_installation_logs(
        self,
        vm_id: Optional[str] = None,
        deployment_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get installation logs.
        
        Args:
            vm_id: Filter by VM ID
            deployment_id: Filter by deployment ID
            limit: Maximum number of logs to return
        
        Returns:
            List of deployment log records
        """
        try:
            if not self.history_file.exists():
                return []
            
            with open(self.history_file, 'r') as f:
                history = json.load(f)
            
            deployments = history.get('deployments', [])
            
            # Apply filters
            filtered = []
            for deployment in deployments:
                if vm_id and deployment.get('vm_id') != vm_id:
                    continue
                if deployment_id and deployment.get('deployment_id') != deployment_id:
                    continue
                filtered.append(deployment)
            
            # Sort by timestamp (newest first)
            filtered.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # Apply limit
            if limit:
                filtered = filtered[:limit]
            
            return filtered
            
        except Exception as e:
            self.logger.error(f"Failed to get installation logs: {e}")
            return []
    
    def get_deployment_summary(self) -> Dict[str, Any]:
        """
        Get deployment summary statistics.
        
        Returns:
            Dictionary with deployment statistics
        """
        try:
            if not self.history_file.exists():
                return {
                    'total_deployments': 0,
                    'by_status': {},
                    'by_vm': {},
                    'recent_deployments': []
                }
            
            with open(self.history_file, 'r') as f:
                history = json.load(f)
            
            deployments = history.get('deployments', [])
            
            summary = {
                'total_deployments': len(deployments),
                'by_status': {},
                'by_vm': {},
                'recent_deployments': deployments[-10:] if len(deployments) > 10 else deployments
            }
            
            for deployment in deployments:
                # Count by status
                status = deployment.get('status', 'unknown')
                summary['by_status'][status] = summary['by_status'].get(status, 0) + 1
                
                # Count by VM
                vm_id = deployment.get('vm_id', 'unknown')
                summary['by_vm'][vm_id] = summary['by_vm'].get(vm_id, 0) + 1
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get deployment summary: {e}")
            return {
                'total_deployments': 0,
                'by_status': {},
                'by_vm': {},
                'error': str(e)
            }
    
    def get_deployment_log_content(self, log_file: str) -> Optional[str]:
        """
        Get content of deployment log file.
        
        Args:
            log_file: Path to log file
        
        Returns:
            Log content or None if not found
        """
        try:
            log_path = Path(log_file)
            if not log_path.is_absolute():
                log_path = self.logs_dir / log_file
            
            if not log_path.exists():
                return None
            
            with open(log_path, 'r') as f:
                return f.read()
                
        except Exception as e:
            self.logger.error(f"Failed to load deployment log from {log_file}: {e}")
            return None
    
    def close(self) -> None:
        """Close connections."""
        if self.remote_executor:
            self.remote_executor.close_connections()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.close()
        except Exception:
            pass

