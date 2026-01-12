"""
Test Runner Service - Remote test execution and management.

This module provides functionality for running tests remotely on VMs,
managing test results, and maintaining test history.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import yaml

from .remote_executor import RemoteExecutor, RemoteExecutorError


class TestRunnerError(Exception):
    """Base exception for test runner errors."""
    pass


class TestRunner:
    """
    Test runner service for remote test execution.
    
    Provides functionality for:
    - Running connection tests remotely
    - Running data flow tests remotely
    - Running health checks on all VMs
    - Managing test results and history
    - Parsing and storing test outputs
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        remote_executor: Optional[RemoteExecutor] = None,
        results_dir: Optional[str] = None,
        history_file: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Test Runner.
        
        Args:
            config_path: Path to config.yml file
            config: Configuration dict (alternative to config_path)
            remote_executor: Optional RemoteExecutor instance
            results_dir: Directory for test results
            history_file: Path to test history file
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
                raise TestRunnerError(
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
        if results_dir:
            self.results_dir = Path(results_dir)
        else:
            project_root = Path(__file__).parent.parent.parent
            self.results_dir = project_root / "test_results"
        
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Test history
        if history_file:
            self.history_file = Path(history_file)
        else:
            project_root = Path(__file__).parent.parent.parent
            self.history_file = project_root / "test_results" / "test_history.json"
        
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_history_file()
        
        # Test script paths
        project_root = Path(__file__).parent.parent.parent
        self.test_scripts = {
            'connections': 'hosts/shared/test_connections.sh',
            'data_flow': 'hosts/shared/test_data_flow.sh',
            'health_check_vm01': 'hosts/vm01-ingest/health_check.sh',
            'health_check_vm02': 'hosts/vm02-database/health_check.sh',
            'health_check_vm03': 'hosts/vm03-analysis/health_check.sh',
            'health_check_vm04': 'hosts/vm04-orchestrator/health_check.sh'
        }
        
        # Determine project root on VMs
        self.vm_project_root = self.config.get('repository', {}).get('vm_repo_paths', {}).get(
            'vm01',
            '/home/thadmin/th_timmy'
        )
        
        self.logger.info("TestRunner initialized")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            self.logger.debug(f"Configuration loaded from {config_path}")
            return config
        except Exception as e:
            raise TestRunnerError(f"Failed to load configuration from {config_path}: {e}")
    
    def _ensure_history_file(self) -> None:
        """Ensure test history file exists."""
        if not self.history_file.exists():
            with open(self.history_file, 'w') as f:
                json.dump({'tests': []}, f, indent=2)
    
    def _add_to_history(self, test_result: Dict[str, Any]) -> None:
        """Add test result to history."""
        try:
            # Load existing history
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
            else:
                history = {'tests': []}
            
            # Add new test result
            history['tests'].append(test_result)
            
            # Keep only last 1000 test results
            if len(history['tests']) > 1000:
                history['tests'] = history['tests'][-1000:]
            
            # Save history
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            self.logger.warning(f"Failed to add test to history: {e}")
    
    def _parse_test_output(self, stdout: str, stderr: str, exit_code: int) -> Dict[str, Any]:
        """
        Parse test script output.
        
        Args:
            stdout: Standard output from test
            stderr: Standard error from test
            exit_code: Exit code from test
        
        Returns:
            Dictionary with parsed test results
        """
        result = {
            'exit_code': exit_code,
            'success': exit_code == 0,
            'stdout': stdout,
            'stderr': stderr,
            'passed': 0,
            'failed': 0,
            'warnings': 0
        }
        
        # Try to extract test counts from output
        output_lines = stdout.split('\n')
        for line in output_lines:
            if 'Passed:' in line or 'passed:' in line:
                try:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'passed' in part.lower():
                            if i + 1 < len(parts):
                                result['passed'] = int(parts[i + 1])
                except (ValueError, IndexError):
                    pass
            elif 'Failed:' in line or 'failed:' in line:
                try:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'failed' in part.lower():
                            if i + 1 < len(parts):
                                result['failed'] = int(parts[i + 1])
                except (ValueError, IndexError):
                    pass
            elif 'Warnings:' in line or 'warnings:' in line or 'Warn' in line:
                try:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'warn' in part.lower():
                            if i + 1 < len(parts):
                                result['warnings'] = int(parts[i + 1])
                except (ValueError, IndexError):
                    pass
        
        return result
    
    def _save_test_result(self, test_result: Dict[str, Any]) -> str:
        """
        Save test result to file.
        
        Args:
            test_result: Test result dictionary
        
        Returns:
            Path to saved result file
        """
        try:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            test_type = test_result.get('test_type', 'unknown')
            filename = f"{test_type}_{timestamp}.json"
            result_path = self.results_dir / filename
            
            with open(result_path, 'w') as f:
                json.dump(test_result, f, indent=2)
            
            test_result['result_file'] = str(result_path)
            return str(result_path)
            
        except Exception as e:
            self.logger.error(f"Failed to save test result: {e}")
            return ""
    
    def run_connection_tests(self, vm_id: str = 'vm04') -> Dict[str, Any]:
        """
        Run connection tests remotely.
        
        Args:
            vm_id: VM identifier to run tests from (default: vm04)
        
        Returns:
            Dictionary with test results
        """
        try:
            self.logger.info(f"Running connection tests from {vm_id}")
            
            test_script = self.test_scripts['connections']
            config_path = f"{self.vm_project_root}/configs/config.yml"
            
            # Execute test script
            command = f"cd {self.vm_project_root} && bash {test_script} {config_path} 2>&1"
            
            exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                vm_id=vm_id,
                command=command,
                timeout=300  # Connection tests might take time
            )
            
            # Parse output
            parsed_result = self._parse_test_output(stdout, stderr, exit_code)
            
            # Create test result
            test_result = {
                'test_type': 'connections',
                'vm_id': vm_id,
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'success' if exit_code == 0 else 'failed',
                **parsed_result
            }
            
            # Save result
            result_file = self._save_test_result(test_result)
            
            # Add to history
            self._add_to_history(test_result)
            
            self.logger.info(
                f"Connection tests completed: "
                f"passed={parsed_result['passed']}, "
                f"failed={parsed_result['failed']}, "
                f"warnings={parsed_result['warnings']}"
            )
            
            return test_result
            
        except RemoteExecutorError as e:
            error_result = {
                'test_type': 'connections',
                'vm_id': vm_id,
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'error',
                'error': str(e)
            }
            self._add_to_history(error_result)
            raise TestRunnerError(f"Failed to run connection tests: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error running connection tests: {e}")
            raise TestRunnerError(f"Unexpected error: {e}")
    
    def run_data_flow_tests(self, vm_id: str = 'vm04') -> Dict[str, Any]:
        """
        Run data flow tests remotely.
        
        Args:
            vm_id: VM identifier to run tests from (default: vm04)
        
        Returns:
            Dictionary with test results
        """
        try:
            self.logger.info(f"Running data flow tests from {vm_id}")
            
            test_script = self.test_scripts['data_flow']
            config_path = f"{self.vm_project_root}/configs/config.yml"
            
            # Execute test script
            command = f"cd {self.vm_project_root} && bash {test_script} {config_path} 2>&1"
            
            exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                vm_id=vm_id,
                command=command,
                timeout=300  # Data flow tests might take time
            )
            
            # Parse output
            parsed_result = self._parse_test_output(stdout, stderr, exit_code)
            
            # Create test result
            test_result = {
                'test_type': 'data_flow',
                'vm_id': vm_id,
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'success' if exit_code == 0 else 'failed',
                **parsed_result
            }
            
            # Save result
            result_file = self._save_test_result(test_result)
            
            # Add to history
            self._add_to_history(test_result)
            
            self.logger.info(
                f"Data flow tests completed: "
                f"passed={parsed_result['passed']}, "
                f"failed={parsed_result['failed']}, "
                f"warnings={parsed_result['warnings']}"
            )
            
            return test_result
            
        except RemoteExecutorError as e:
            error_result = {
                'test_type': 'data_flow',
                'vm_id': vm_id,
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'error',
                'error': str(e)
            }
            self._add_to_history(error_result)
            raise TestRunnerError(f"Failed to run data flow tests: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error running data flow tests: {e}")
            raise TestRunnerError(f"Unexpected error: {e}")
    
    def run_health_check(self, vm_id: str) -> Dict[str, Any]:
        """
        Run health check on specific VM.
        
        Args:
            vm_id: VM identifier
        
        Returns:
            Dictionary with health check results
        """
        try:
            self.logger.info(f"Running health check on {vm_id}")
            
            # Get health check script for VM
            script_key = f'health_check_{vm_id}'
            if script_key not in self.test_scripts:
                raise TestRunnerError(f"No health check script for {vm_id}")
            
            test_script = self.test_scripts[script_key]
            
            # Execute health check script
            command = f"cd {self.vm_project_root} && bash {test_script} {self.vm_project_root} 2>&1"
            
            exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                vm_id=vm_id,
                command=command,
                timeout=180  # Health checks might take time
            )
            
            # Parse output
            parsed_result = self._parse_test_output(stdout, stderr, exit_code)
            
            # Determine health status
            if exit_code == 0 and parsed_result['failed'] == 0:
                health_status = 'healthy'
            elif exit_code == 0 and parsed_result['failed'] > 0:
                health_status = 'unhealthy'
            elif parsed_result['warnings'] > 0:
                health_status = 'degraded'
            else:
                health_status = 'unhealthy'
            
            # Create test result
            test_result = {
                'test_type': 'health_check',
                'vm_id': vm_id,
                'timestamp': datetime.utcnow().isoformat(),
                'status': health_status,
                'exit_code': exit_code,
                **parsed_result
            }
            
            # Save result
            result_file = self._save_test_result(test_result)
            
            # Add to history
            self._add_to_history(test_result)
            
            self.logger.info(f"Health check on {vm_id} completed: {health_status}")
            
            return test_result
            
        except RemoteExecutorError as e:
            error_result = {
                'test_type': 'health_check',
                'vm_id': vm_id,
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'error',
                'error': str(e)
            }
            self._add_to_history(error_result)
            raise TestRunnerError(f"Failed to run health check on {vm_id}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error running health check on {vm_id}: {e}")
            raise TestRunnerError(f"Unexpected error: {e}")
    
    def run_health_checks_all(self) -> Dict[str, Any]:
        """
        Run health checks on all enabled VMs.
        
        Returns:
            Dictionary with results for all VMs
        """
        try:
            self.logger.info("Running health checks on all VMs")
            
            vms = self.config.get('vms', {})
            enabled_vms = [
                vm_id for vm_id, vm_config in vms.items()
                if vm_config.get('enabled', True)
            ]
            
            results = {}
            healthy_count = 0
            unhealthy_count = 0
            degraded_count = 0
            error_count = 0
            
            for vm_id in enabled_vms:
                try:
                    result = self.run_health_check(vm_id)
                    results[vm_id] = result
                    
                    status = result.get('status', 'unknown')
                    if status == 'healthy':
                        healthy_count += 1
                    elif status == 'unhealthy':
                        unhealthy_count += 1
                    elif status == 'degraded':
                        degraded_count += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    self.logger.error(f"Failed to run health check on {vm_id}: {e}")
                    results[vm_id] = {
                        'test_type': 'health_check',
                        'vm_id': vm_id,
                        'timestamp': datetime.utcnow().isoformat(),
                        'status': 'error',
                        'error': str(e)
                    }
                    error_count += 1
            
            summary = {
                'timestamp': datetime.utcnow().isoformat(),
                'test_type': 'health_checks_all',
                'summary': {
                    'total': len(enabled_vms),
                    'healthy': healthy_count,
                    'unhealthy': unhealthy_count,
                    'degraded': degraded_count,
                    'errors': error_count
                },
                'results': results
            }
            
            # Save summary
            self._save_test_result(summary)
            self._add_to_history(summary)
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to run health checks on all VMs: {e}")
            raise TestRunnerError(f"Failed to run health checks: {e}")
    
    def get_test_history(
        self,
        test_type: Optional[str] = None,
        vm_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get test history.
        
        Args:
            test_type: Filter by test type
            vm_id: Filter by VM ID
            limit: Maximum number of results to return
        
        Returns:
            List of test results
        """
        try:
            if not self.history_file.exists():
                return []
            
            with open(self.history_file, 'r') as f:
                history = json.load(f)
            
            tests = history.get('tests', [])
            
            # Apply filters
            filtered = []
            for test in tests:
                if test_type and test.get('test_type') != test_type:
                    continue
                if vm_id and test.get('vm_id') != vm_id:
                    continue
                filtered.append(test)
            
            # Sort by timestamp (newest first)
            filtered.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # Apply limit
            if limit:
                filtered = filtered[:limit]
            
            return filtered
            
        except Exception as e:
            self.logger.error(f"Failed to get test history: {e}")
            return []
    
    def get_test_result(self, result_file: str) -> Optional[Dict[str, Any]]:
        """
        Get test result from file.
        
        Args:
            result_file: Path to result file
        
        Returns:
            Test result dictionary or None if not found
        """
        try:
            result_path = Path(result_file)
            if not result_path.is_absolute():
                result_path = self.results_dir / result_file
            
            if not result_path.exists():
                return None
            
            with open(result_path, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            self.logger.error(f"Failed to load test result from {result_file}: {e}")
            return None
    
    def get_test_summary(self) -> Dict[str, Any]:
        """
        Get summary of all tests.
        
        Returns:
            Dictionary with test statistics
        """
        try:
            if not self.history_file.exists():
                return {
                    'total_tests': 0,
                    'by_type': {},
                    'by_status': {},
                    'by_vm': {}
                }
            
            with open(self.history_file, 'r') as f:
                history = json.load(f)
            
            tests = history.get('tests', [])
            
            summary = {
                'total_tests': len(tests),
                'by_type': {},
                'by_status': {},
                'by_vm': {},
                'recent_tests': tests[-10:] if len(tests) > 10 else tests
            }
            
            for test in tests:
                # Count by type
                test_type = test.get('test_type', 'unknown')
                summary['by_type'][test_type] = summary['by_type'].get(test_type, 0) + 1
                
                # Count by status
                status = test.get('status', 'unknown')
                summary['by_status'][status] = summary['by_status'].get(status, 0) + 1
                
                # Count by VM
                vm_id = test.get('vm_id', 'unknown')
                summary['by_vm'][vm_id] = summary['by_vm'].get(vm_id, 0) + 1
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get test summary: {e}")
            return {
                'total_tests': 0,
                'by_type': {},
                'by_status': {},
                'by_vm': {},
                'error': str(e)
            }
    
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

