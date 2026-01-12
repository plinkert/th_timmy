"""
Hardening Manager Service - Remote hardening management.

This module provides functionality for managing security hardening remotely,
including hardening execution, status checking, before/after comparison,
and hardening reports.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import yaml

from .remote_executor import RemoteExecutor, RemoteExecutorError
from .test_runner import TestRunner, TestRunnerError


class HardeningManagerError(Exception):
    """Base exception for hardening manager errors."""
    pass


class HardeningManager:
    """
    Hardening management service.
    
    Provides functionality for:
    - Checking hardening status on VMs
    - Running hardening scripts remotely
    - Comparing before/after hardening
    - Generating hardening reports
    - Managing hardening history
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        remote_executor: Optional[RemoteExecutor] = None,
        test_runner: Optional[TestRunner] = None,
        reports_dir: Optional[str] = None,
        history_file: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Hardening Manager.
        
        Args:
            config_path: Path to config.yml file
            config: Configuration dict (alternative to config_path)
            remote_executor: Optional RemoteExecutor instance
            test_runner: Optional TestRunner instance
            reports_dir: Directory for hardening reports
            history_file: Path to hardening history file
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
                raise HardeningManagerError(
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
        
        # Initialize test runner
        if test_runner:
            self.test_runner = test_runner
        else:
            self.test_runner = TestRunner(
                config=self.config,
                remote_executor=self.remote_executor,
                logger=self.logger
            )
        
        # Setup directories
        if reports_dir:
            self.reports_dir = Path(reports_dir)
        else:
            project_root = Path(__file__).parent.parent.parent
            self.reports_dir = project_root / "logs" / "hardening"
        
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Hardening history
        if history_file:
            self.history_file = Path(history_file)
        else:
            project_root = Path(__file__).parent.parent.parent
            self.history_file = project_root / "logs" / "hardening" / "hardening_history.json"
        
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_history_file()
        
        # Hardening script paths
        project_root = Path(__file__).parent.parent.parent
        self.hardening_scripts = {
            'vm01': 'hosts/vm01-ingest/harden_vm01.sh',
            'vm02': 'hosts/vm02-database/harden_vm02.sh',
            'vm03': 'hosts/vm03-analysis/harden_vm03.sh',
            'vm04': 'hosts/vm04-orchestrator/harden_vm04.sh'
        }
        
        # Determine project root on VMs
        # Try configuration_management first, then repository
        self.vm_project_root = None
        if 'configuration_management' in self.config:
            vm_paths = self.config.get('configuration_management', {}).get('vm_config_paths', {})
            if 'vm01' in vm_paths:
                # Extract directory from config path
                config_path = vm_paths['vm01']
                self.vm_project_root = str(Path(config_path).parent.parent)
        
        if not self.vm_project_root:
            self.vm_project_root = self.config.get('repository', {}).get('vm_repo_paths', {}).get(
                'vm01',
                '/home/thadmin/th_timmy'
            )
        
        self.logger.info("HardeningManager initialized")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            self.logger.debug(f"Configuration loaded from {config_path}")
            return config
        except Exception as e:
            raise HardeningManagerError(f"Failed to load configuration from {config_path}: {e}")
    
    def _ensure_history_file(self) -> None:
        """Ensure hardening history file exists."""
        if not self.history_file.exists():
            with open(self.history_file, 'w') as f:
                json.dump({'hardening_operations': []}, f, indent=2)
    
    def _add_to_history(self, hardening_record: Dict[str, Any]) -> None:
        """Add hardening record to history."""
        try:
            # Load existing history
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
            else:
                history = {'hardening_operations': []}
            
            # Add new hardening record
            history['hardening_operations'].append(hardening_record)
            
            # Keep only last 500 hardening records
            if len(history['hardening_operations']) > 500:
                history['hardening_operations'] = history['hardening_operations'][-500:]
            
            # Save history
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            self.logger.warning(f"Failed to add hardening to history: {e}")
    
    def _save_hardening_log(
        self,
        vm_id: str,
        log_content: str,
        hardening_id: str
    ) -> str:
        """
        Save hardening log to file.
        
        Args:
            vm_id: VM identifier
            log_content: Log content
            hardening_id: Hardening ID
        
        Returns:
            Path to saved log file
        """
        try:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"hardening_{vm_id}_{hardening_id}_{timestamp}.log"
            log_path = self.reports_dir / filename
            
            with open(log_path, 'w') as f:
                f.write(log_content)
            
            return str(log_path)
            
        except Exception as e:
            self.logger.error(f"Failed to save hardening log: {e}")
            return ""
    
    def _parse_hardening_output(
        self,
        stdout: str,
        stderr: str,
        exit_code: int
    ) -> Dict[str, Any]:
        """
        Parse hardening script output.
        
        Args:
            stdout: Standard output from hardening
            stderr: Standard error from hardening
            exit_code: Exit code from hardening
        
        Returns:
            Dictionary with parsed hardening results
        """
        result = {
            'exit_code': exit_code,
            'success': exit_code == 0,
            'stdout': stdout,
            'stderr': stderr,
            'hardened_components': [],
            'warnings': [],
            'errors': []
        }
        
        # Try to extract information from output
        output_lines = stdout.split('\n')
        for line in output_lines:
            # Look for hardened components
            if '[INFO]' in line or 'Hardening' in line or 'Configured' in line:
                if 'Hardening' in line or 'Configured' in line or 'installed' in line.lower():
                    result['hardened_components'].append(line.strip())
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
    
    def get_hardening_status(self, vm_id: str) -> Dict[str, Any]:
        """
        Get hardening status for VM.
        
        Args:
            vm_id: VM identifier
        
        Returns:
            Dictionary with hardening status
        """
        try:
            self.logger.info(f"Checking hardening status for {vm_id}")
            
            # Check hardening components
            status_checks = {
                'firewall': False,
                'ssh_hardened': False,
                'fail2ban': False,
                'auto_updates': False,
                'log_rotation': False
            }
            
            # Check firewall (ufw)
            try:
                exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                    vm_id=vm_id,
                    command="sudo ufw status | grep -q 'Status: active' && echo 'active' || echo 'inactive'",
                    timeout=10
                )
                if 'active' in stdout:
                    status_checks['firewall'] = True
            except Exception:
                pass
            
            # Check SSH hardening (root login disabled)
            try:
                exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                    vm_id=vm_id,
                    command="sudo grep -q '^PermitRootLogin no' /etc/ssh/sshd_config && echo 'hardened' || echo 'not_hardened'",
                    timeout=10
                )
                if 'hardened' in stdout:
                    status_checks['ssh_hardened'] = True
            except Exception:
                pass
            
            # Check fail2ban
            try:
                exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                    vm_id=vm_id,
                    command="sudo systemctl is-active fail2ban 2>&1 | grep -q 'active' && echo 'active' || echo 'inactive'",
                    timeout=10
                )
                if 'active' in stdout:
                    status_checks['fail2ban'] = True
            except Exception:
                pass
            
            # Check auto updates (unattended-upgrades)
            try:
                exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                    vm_id=vm_id,
                    command="sudo systemctl is-enabled unattended-upgrades 2>&1 | grep -q 'enabled' && echo 'enabled' || echo 'disabled'",
                    timeout=10
                )
                if 'enabled' in stdout:
                    status_checks['auto_updates'] = True
            except Exception:
                pass
            
            # Check log rotation
            try:
                exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                    vm_id=vm_id,
                    command="test -f /etc/logrotate.d/threat-hunting-vm* && echo 'configured' || echo 'not_configured'",
                    timeout=10
                )
                if 'configured' in stdout:
                    status_checks['log_rotation'] = True
            except Exception:
                pass
            
            # Determine overall status
            hardened_count = sum(1 for v in status_checks.values() if v)
            total_checks = len(status_checks)
            
            if hardened_count == total_checks:
                overall_status = 'hardened'
            elif hardened_count > 0:
                overall_status = 'partial'
            else:
                overall_status = 'not_hardened'
            
            return {
                'vm_id': vm_id,
                'status': overall_status,
                'checks': status_checks,
                'hardened_count': hardened_count,
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
            self.logger.error(f"Failed to get hardening status for {vm_id}: {e}")
            return {
                'vm_id': vm_id,
                'status': 'unknown',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_hardening_status_all(self) -> Dict[str, Any]:
        """
        Get hardening status for all enabled VMs.
        
        Returns:
            Dictionary with hardening status for all VMs
        """
        try:
            vms = self.config.get('vms', {})
            enabled_vms = [
                vm_id for vm_id, vm_config in vms.items()
                if vm_config.get('enabled', True)
            ]
            
            results = {}
            hardened_count = 0
            partial_count = 0
            not_hardened_count = 0
            
            for vm_id in enabled_vms:
                status = self.get_hardening_status(vm_id)
                results[vm_id] = status
                
                status_value = status.get('status', 'unknown')
                if status_value == 'hardened':
                    hardened_count += 1
                elif status_value == 'partial':
                    partial_count += 1
                else:
                    not_hardened_count += 1
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'summary': {
                    'total': len(enabled_vms),
                    'hardened': hardened_count,
                    'partial': partial_count,
                    'not_hardened': not_hardened_count
                },
                'vms': results
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get hardening status for all VMs: {e}")
            raise HardeningManagerError(f"Failed to get hardening status: {e}")
    
    def run_hardening(
        self,
        vm_id: str,
        project_root: Optional[str] = None,
        capture_before: bool = True
    ) -> Dict[str, Any]:
        """
        Run hardening script on VM.
        
        Args:
            vm_id: VM identifier
            project_root: Project root path on VM (default: from config)
            capture_before: Whether to capture system state before hardening
        
        Returns:
            Dictionary with hardening results
        """
        try:
            self.logger.info(f"Starting hardening on {vm_id}")
            
            if vm_id not in self.hardening_scripts:
                raise HardeningManagerError(f"No hardening script for {vm_id}")
            
            hardening_script = self.hardening_scripts[vm_id]
            
            if not project_root:
                project_root = self.vm_project_root
            
            # Generate hardening ID
            hardening_id = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            
            # Capture before state if requested
            before_state = None
            if capture_before:
                try:
                    before_state = self.get_hardening_status(vm_id)
                except Exception as e:
                    self.logger.warning(f"Failed to capture before state: {e}")
            
            # Execute hardening script with sudo
            # Note: Hardening scripts require root privileges
            command = f"cd {project_root} && sudo bash {hardening_script} 2>&1"
            
            self.logger.info(f"Executing hardening command on {vm_id}")
            
            exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                vm_id=vm_id,
                command=command,
                timeout=1800  # Hardening can take up to 30 minutes
            )
            
            # Parse output
            parsed_result = self._parse_hardening_output(stdout, stderr, exit_code)
            
            # Capture after state
            after_state = None
            try:
                after_state = self.get_hardening_status(vm_id)
            except Exception as e:
                self.logger.warning(f"Failed to capture after state: {e}")
            
            # Save log
            log_content = f"=== Hardening Log for {vm_id} ===\n"
            log_content += f"Hardening ID: {hardening_id}\n"
            log_content += f"Timestamp: {datetime.utcnow().isoformat()}\n"
            log_content += f"Exit Code: {exit_code}\n\n"
            log_content += "=== BEFORE STATE ===\n"
            log_content += json.dumps(before_state, indent=2) if before_state else "Not captured\n"
            log_content += "\n\n=== STDOUT ===\n"
            log_content += stdout
            log_content += "\n\n=== STDERR ===\n"
            log_content += stderr
            log_content += "\n\n=== AFTER STATE ===\n"
            log_content += json.dumps(after_state, indent=2) if after_state else "Not captured\n"
            
            log_path = self._save_hardening_log(vm_id, log_content, hardening_id)
            
            # Create hardening record
            hardening_record = {
                'hardening_id': hardening_id,
                'vm_id': vm_id,
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'success' if exit_code == 0 else 'failed',
                'exit_code': exit_code,
                'log_file': log_path,
                'before_state': before_state,
                'after_state': after_state,
                'hardened_components': parsed_result.get('hardened_components', []),
                'warnings': parsed_result.get('warnings', []),
                'errors': parsed_result.get('errors', [])
            }
            
            # Add to history
            self._add_to_history(hardening_record)
            
            self.logger.info(
                f"Hardening on {vm_id} completed: "
                f"status={hardening_record['status']}, "
                f"exit_code={exit_code}"
            )
            
            return hardening_record
            
        except RemoteExecutorError as e:
            error_record = {
                'hardening_id': datetime.utcnow().strftime('%Y%m%d_%H%M%S'),
                'vm_id': vm_id,
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'error',
                'error': str(e)
            }
            self._add_to_history(error_record)
            raise HardeningManagerError(f"Failed to run hardening on {vm_id}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error running hardening on {vm_id}: {e}")
            raise HardeningManagerError(f"Unexpected error: {e}")
    
    def compare_before_after(
        self,
        hardening_id: str,
        vm_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare before/after hardening state.
        
        Args:
            hardening_id: Hardening ID
            vm_id: Optional VM identifier filter
        
        Returns:
            Dictionary with comparison results
        """
        try:
            if not self.history_file.exists():
                raise HardeningManagerError("Hardening history file not found")
            
            with open(self.history_file, 'r') as f:
                history = json.load(f)
            
            # Find hardening record
            operations = history.get('hardening_operations', [])
            matching = [
                op for op in operations
                if op.get('hardening_id') == hardening_id
                and (not vm_id or op.get('vm_id') == vm_id)
            ]
            
            if not matching:
                raise HardeningManagerError(f"Hardening record not found: {hardening_id}")
            
            record = matching[0]
            before_state = record.get('before_state')
            after_state = record.get('after_state')
            
            if not before_state or not after_state:
                return {
                    'hardening_id': hardening_id,
                    'vm_id': record.get('vm_id'),
                    'comparison': 'incomplete',
                    'message': 'Before or after state not captured',
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            # Compare states
            before_checks = before_state.get('checks', {})
            after_checks = after_state.get('checks', {})
            
            changes = {}
            for check_name in before_checks:
                before_value = before_checks.get(check_name, False)
                after_value = after_checks.get(check_name, False)
                
                if before_value != after_value:
                    changes[check_name] = {
                        'before': before_value,
                        'after': after_value,
                        'changed': True
                    }
                else:
                    changes[check_name] = {
                        'before': before_value,
                        'after': after_value,
                        'changed': False
                    }
            
            before_status = before_state.get('status', 'unknown')
            after_status = after_state.get('status', 'unknown')
            
            return {
                'hardening_id': hardening_id,
                'vm_id': record.get('vm_id'),
                'timestamp': datetime.utcnow().isoformat(),
                'before_status': before_status,
                'after_status': after_status,
                'status_changed': before_status != after_status,
                'changes': changes,
                'summary': {
                    'total_checks': len(changes),
                    'changed': sum(1 for c in changes.values() if c.get('changed')),
                    'unchanged': sum(1 for c in changes.values() if not c.get('changed'))
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to compare before/after: {e}")
            raise HardeningManagerError(f"Failed to compare: {e}")
    
    def get_hardening_reports(
        self,
        vm_id: Optional[str] = None,
        hardening_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get hardening reports.
        
        Args:
            vm_id: Filter by VM ID
            hardening_id: Filter by hardening ID
            limit: Maximum number of reports to return
        
        Returns:
            List of hardening report records
        """
        try:
            if not self.history_file.exists():
                return []
            
            with open(self.history_file, 'r') as f:
                history = json.load(f)
            
            operations = history.get('hardening_operations', [])
            
            # Apply filters
            filtered = []
            for operation in operations:
                if vm_id and operation.get('vm_id') != vm_id:
                    continue
                if hardening_id and operation.get('hardening_id') != hardening_id:
                    continue
                filtered.append(operation)
            
            # Sort by timestamp (newest first)
            filtered.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # Apply limit
            if limit:
                filtered = filtered[:limit]
            
            return filtered
            
        except Exception as e:
            self.logger.error(f"Failed to get hardening reports: {e}")
            return []
    
    def get_hardening_summary(self) -> Dict[str, Any]:
        """
        Get hardening summary statistics.
        
        Returns:
            Dictionary with hardening statistics
        """
        try:
            if not self.history_file.exists():
                return {
                    'total_operations': 0,
                    'by_status': {},
                    'by_vm': {},
                    'recent_operations': []
                }
            
            with open(self.history_file, 'r') as f:
                history = json.load(f)
            
            operations = history.get('hardening_operations', [])
            
            summary = {
                'total_operations': len(operations),
                'by_status': {},
                'by_vm': {},
                'recent_operations': operations[-10:] if len(operations) > 10 else operations
            }
            
            for operation in operations:
                # Count by status
                op_status = operation.get('status', 'unknown')
                summary['by_status'][op_status] = summary['by_status'].get(op_status, 0) + 1
                
                # Count by VM
                op_vm_id = operation.get('vm_id', 'unknown')
                summary['by_vm'][op_vm_id] = summary['by_vm'].get(op_vm_id, 0) + 1
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get hardening summary: {e}")
            return {
                'total_operations': 0,
                'by_status': {},
                'by_vm': {},
                'error': str(e)
            }
    
    def get_hardening_log_content(self, log_file: str) -> Optional[str]:
        """
        Get content of hardening log file.
        
        Args:
            log_file: Path to log file
        
        Returns:
            Log content or None if not found
        """
        try:
            log_path = Path(log_file)
            if not log_path.is_absolute():
                log_path = self.reports_dir / log_file
            
            if not log_path.exists():
                return None
            
            with open(log_path, 'r') as f:
                return f.read()
                
        except Exception as e:
            self.logger.error(f"Failed to load hardening log from {log_file}: {e}")
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

