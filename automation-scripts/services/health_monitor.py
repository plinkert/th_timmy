"""
Health Monitoring Service - Central health monitoring for all VMs.

This module provides comprehensive health monitoring functionality including
health checks, metrics collection, alerting, and scheduled monitoring.
"""

import os
import logging
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import yaml

from .remote_executor import RemoteExecutor, RemoteExecutorError
from .metrics_collector import MetricsCollector, MetricsCollectorError

# Try relative import first, fallback to direct import if relative import fails
try:
    from ..utils.alert_manager import AlertManager, AlertLevel
except (ImportError, ValueError):
    from utils.alert_manager import AlertManager, AlertLevel


class HealthMonitorError(Exception):
    """Base exception for health monitor errors."""
    pass


class HealthMonitor:
    """
    Health monitoring service.
    
    Provides functionality for:
    - Checking VM health using health_check.sh scripts
    - Collecting metrics from VMs
    - Scheduling periodic health checks
    - Managing alerts based on health status
    - Aggregating health status across all VMs
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        remote_executor: Optional[RemoteExecutor] = None,
        alert_manager: Optional[AlertManager] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Health Monitor.
        
        Args:
            config_path: Path to config.yml file
            config: Configuration dict (alternative to config_path)
            remote_executor: Optional RemoteExecutor instance
            alert_manager: Optional AlertManager instance
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
                raise HealthMonitorError(
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
        
        # Initialize metrics collector
        self.metrics_collector = MetricsCollector(
            remote_executor=self.remote_executor,
            logger=self.logger
        )
        
        # Initialize alert manager
        if alert_manager:
            self.alert_manager = alert_manager
        else:
            alert_history_file = self.config.get('health_monitoring', {}).get(
                'alert_history_file',
                'logs/alerts_history.json'
            )
            self.alert_manager = AlertManager(
                alert_history_file=alert_history_file,
                logger=self.logger
            )
        
        # Health check scheduling
        self._scheduled_checks = {}
        self._scheduler_thread = None
        self._scheduler_running = False
        
        # Health check script paths
        self.health_check_scripts = {
            'vm01': 'hosts/vm01-ingest/health_check.sh',
            'vm02': 'hosts/vm02-database/health_check.sh',
            'vm03': 'hosts/vm03-analysis/health_check.sh',
            'vm04': 'hosts/vm04-orchestrator/health_check.sh'
        }
        
        self.logger.info("HealthMonitor initialized")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            self.logger.debug(f"Configuration loaded from {config_path}")
            return config
        except Exception as e:
            raise HealthMonitorError(f"Failed to load configuration from {config_path}: {e}")
    
    def check_vm_health(self, vm_id: str) -> Dict[str, Any]:
        """
        Check VM health using health_check.sh script.
        
        Args:
            vm_id: VM identifier
        
        Returns:
            Dictionary with health check results
        """
        try:
            self.logger.info(f"Checking health for {vm_id}")
            
            # Get health check script path
            script_path = self.health_check_scripts.get(vm_id)
            if not script_path:
                raise HealthMonitorError(f"No health check script configured for {vm_id}")
            
            # Determine project root on VM
            # Try configuration_management first, then repository
            project_root = None
            if 'configuration_management' in self.config:
                vm_paths = self.config.get('configuration_management', {}).get('vm_config_paths', {})
                if vm_id in vm_paths:
                    # Extract directory from config path
                    config_path = vm_paths[vm_id]
                    project_root = str(Path(config_path).parent.parent)
            
            if not project_root:
                project_root = self.config.get('repository', {}).get('vm_repo_paths', {}).get(
                    vm_id,
                    '/home/thadmin/th_timmy'
                )
            
            # Execute health check script
            health_check_command = f"cd {project_root} && bash {script_path} {project_root} 2>&1"
            
            exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                vm_id=vm_id,
                command=health_check_command,
                timeout=120  # Health checks might take time
            )
            
            # Parse health check output
            health_status = self._parse_health_check_output(stdout, stderr, exit_code)
            health_status['vm_id'] = vm_id
            health_status['timestamp'] = datetime.utcnow().isoformat()
            health_status['exit_code'] = exit_code
            
            # Collect metrics
            try:
                metrics = self.metrics_collector.collect_metrics(vm_id)
                health_status['metrics'] = metrics
            except Exception as e:
                self.logger.warning(f"Failed to collect metrics for {vm_id}: {e}")
                health_status['metrics'] = {'error': str(e)}
            
            # Check for issues and send alerts
            self._check_and_alert(health_status)
            
            return health_status
            
        except RemoteExecutorError as e:
            error_status = {
                'vm_id': vm_id,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Send critical alert for unreachable VM
            self.alert_manager.send_alert(
                level='critical',
                message=f"VM {vm_id} is unreachable: {e}",
                vm_id=vm_id
            )
            
            return error_status
        except Exception as e:
            self.logger.error(f"Failed to check health for {vm_id}: {e}")
            raise HealthMonitorError(f"Health check failed for {vm_id}: {e}")
    
    def _parse_health_check_output(
        self,
        stdout: str,
        stderr: str,
        exit_code: int
    ) -> Dict[str, Any]:
        """
        Parse health check script output.
        
        Args:
            stdout: Standard output from health check
            stderr: Standard error from health check
            exit_code: Exit code from health check
        
        Returns:
            Dictionary with parsed health status
        """
        status = {
            'status': 'healthy' if exit_code == 0 else 'unhealthy',
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'details': stdout
        }
        
        # Try to extract counts from output
        if 'Passed:' in stdout:
            try:
                for line in stdout.split('\n'):
                    if 'Passed:' in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'Passed:':
                                if i + 1 < len(parts):
                                    status['passed'] = int(parts[i + 1])
                    elif 'Failed:' in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'Failed:':
                                if i + 1 < len(parts):
                                    status['failed'] = int(parts[i + 1])
                    elif 'Warnings:' in line or 'Warn' in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if 'Warn' in part:
                                if i + 1 < len(parts):
                                    status['warnings'] = int(parts[i + 1])
            except Exception as e:
                self.logger.debug(f"Failed to parse health check counts: {e}")
        
        # Determine overall status
        if exit_code != 0 or status['failed'] > 0:
            status['status'] = 'unhealthy'
        elif status['warnings'] > 0:
            status['status'] = 'degraded'
        else:
            status['status'] = 'healthy'
        
        return status
    
    def _check_and_alert(self, health_status: Dict[str, Any]) -> None:
        """
        Check health status and send alerts if needed.
        
        Args:
            health_status: Health status dictionary
        """
        vm_id = health_status.get('vm_id')
        status = health_status.get('status')
        
        if status == 'unhealthy':
            # Critical alert for unhealthy VM
            self.alert_manager.send_alert(
                level='critical',
                message=f"VM {vm_id} is unhealthy. Failed checks: {health_status.get('failed', 0)}",
                vm_id=vm_id,
                component='health_check'
            )
        elif status == 'degraded':
            # Warning for degraded VM
            self.alert_manager.send_alert(
                level='warning',
                message=f"VM {vm_id} is degraded. Warnings: {health_status.get('warnings', 0)}",
                vm_id=vm_id,
                component='health_check'
            )
        
        # Check metrics for issues
        metrics = health_status.get('metrics', {})
        
        # Check CPU
        cpu_usage = metrics.get('system_resources', {}).get('cpu_usage_percent')
        if cpu_usage is not None and cpu_usage > 90:
            self.alert_manager.send_alert(
                level='warning',
                message=f"VM {vm_id} CPU usage is high: {cpu_usage:.1f}%",
                vm_id=vm_id,
                component='system_resources'
            )
        
        # Check memory
        memory_usage = metrics.get('system_resources', {}).get('memory_usage_percent')
        if memory_usage is not None and memory_usage > 90:
            self.alert_manager.send_alert(
                level='warning',
                message=f"VM {vm_id} memory usage is high: {memory_usage:.1f}%",
                vm_id=vm_id,
                component='system_resources'
            )
        
        # Check disk
        disk_usage = metrics.get('disk', {}).get('root_usage_percent')
        if disk_usage is not None and disk_usage > 90:
            self.alert_manager.send_alert(
                level='critical',
                message=f"VM {vm_id} disk usage is critical: {disk_usage}%",
                vm_id=vm_id,
                component='disk'
            )
        elif disk_usage is not None and disk_usage > 80:
            self.alert_manager.send_alert(
                level='warning',
                message=f"VM {vm_id} disk usage is high: {disk_usage}%",
                vm_id=vm_id,
                component='disk'
            )
        
        # Check services
        services = metrics.get('services', {})
        for service_name, service_status in services.items():
            if isinstance(service_status, dict) and not service_status.get('running', True):
                self.alert_manager.send_alert(
                    level='error',
                    message=f"Service {service_name} is not running on VM {vm_id}",
                    vm_id=vm_id,
                    component=service_name
                )
    
    def collect_metrics(self, vm_id: str) -> Dict[str, Any]:
        """
        Collect metrics for VM.
        
        Args:
            vm_id: VM identifier
        
        Returns:
            Dictionary with collected metrics
        """
        return self.metrics_collector.collect_metrics(vm_id)
    
    def get_health_status_all(self) -> Dict[str, Any]:
        """
        Get health status for all enabled VMs.
        
        Returns:
            Dictionary with health status for all VMs
        """
        try:
            vms = self.config.get('vms', {})
            enabled_vms = [
                vm_id for vm_id, vm_config in vms.items()
                if vm_config.get('enabled', True)
            ]
            
            results = {}
            healthy_count = 0
            unhealthy_count = 0
            degraded_count = 0
            
            for vm_id in enabled_vms:
                try:
                    health_status = self.check_vm_health(vm_id)
                    results[vm_id] = health_status
                    
                    status = health_status.get('status', 'unknown')
                    if status == 'healthy':
                        healthy_count += 1
                    elif status == 'unhealthy':
                        unhealthy_count += 1
                    elif status == 'degraded':
                        degraded_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to check health for {vm_id}: {e}")
                    results[vm_id] = {
                        'status': 'error',
                        'error': str(e),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    unhealthy_count += 1
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'summary': {
                    'total': len(enabled_vms),
                    'healthy': healthy_count,
                    'unhealthy': unhealthy_count,
                    'degraded': degraded_count
                },
                'vms': results
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get health status for all VMs: {e}")
            raise HealthMonitorError(f"Failed to get health status: {e}")
    
    def schedule_health_checks(self, interval: int = 300) -> None:
        """
        Schedule periodic health checks.
        
        Args:
            interval: Interval between health checks in seconds (default: 300 = 5 minutes)
        """
        if self._scheduler_running:
            self.logger.warning("Health check scheduler is already running")
            return
        
        self._scheduler_running = True
        self._check_interval = interval
        
        def scheduler_loop():
            self.logger.info(f"Health check scheduler started (interval: {interval}s)")
            
            while self._scheduler_running:
                try:
                    # Run health checks for all VMs
                    self.logger.info("Running scheduled health checks...")
                    self.get_health_status_all()
                    
                    # Wait for next interval
                    time.sleep(interval)
                    
                except Exception as e:
                    self.logger.error(f"Error in health check scheduler: {e}")
                    time.sleep(interval)
        
        self._scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        
        self.logger.info("Health check scheduler started")
    
    def stop_health_checks(self) -> None:
        """Stop scheduled health checks."""
        if not self._scheduler_running:
            return
        
        self._scheduler_running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        
        self.logger.info("Health check scheduler stopped")
    
    def send_alert(
        self,
        level: str,
        message: str,
        vm_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send alert.
        
        Args:
            level: Alert level ('info', 'warning', 'error', 'critical')
            message: Alert message
            vm_id: Optional VM identifier
        
        Returns:
            Dictionary with alert information
        """
        return self.alert_manager.send_alert(
            level=level,
            message=message,
            vm_id=vm_id
        )
    
    def get_alerts(
        self,
        level: Optional[str] = None,
        vm_id: Optional[str] = None,
        unacknowledged_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get alerts.
        
        Args:
            level: Filter by alert level
            vm_id: Filter by VM ID
            unacknowledged_only: Return only unacknowledged alerts
        
        Returns:
            List of alerts
        """
        return self.alert_manager.get_alerts(
            level=level,
            vm_id=vm_id,
            acknowledged=not unacknowledged_only if unacknowledged_only else None
        )
    
    def close(self) -> None:
        """Close connections and stop scheduler."""
        self.stop_health_checks()
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

