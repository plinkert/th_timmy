"""
Metrics Collector - System and service metrics collection.

This module provides functionality for collecting metrics from VMs
including system resources, service status, and network connectivity.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from .remote_executor import RemoteExecutor, RemoteExecutorError


class MetricsCollectorError(Exception):
    """Base exception for metrics collector errors."""
    pass


class MetricsCollector:
    """
    Metrics collection service.
    
    Provides functionality for:
    - Collecting system resource metrics (CPU, RAM, disk)
    - Checking service status
    - Monitoring network connectivity
    - Collecting configuration validity metrics
    """
    
    def __init__(
        self,
        remote_executor: RemoteExecutor,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Metrics Collector.
        
        Args:
            remote_executor: RemoteExecutor instance for remote operations
            logger: Optional logger instance
        """
        self.remote_executor = remote_executor
        self.logger = logger or logging.getLogger(__name__)
        
        self.logger.debug("MetricsCollector initialized")
    
    def collect_metrics(self, vm_id: str) -> Dict[str, Any]:
        """
        Collect all metrics for VM.
        
        Args:
            vm_id: VM identifier
        
        Returns:
            Dictionary with collected metrics
        """
        try:
            self.logger.info(f"Collecting metrics for {vm_id}")
            
            metrics = {
                'vm_id': vm_id,
                'timestamp': datetime.utcnow().isoformat(),
                'system_resources': self._collect_system_resources(vm_id),
                'services': self._collect_service_status(vm_id),
                'network': self._collect_network_metrics(vm_id),
                'disk': self._collect_disk_metrics(vm_id)
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to collect metrics for {vm_id}: {e}")
            raise MetricsCollectorError(f"Failed to collect metrics: {e}")
    
    def _collect_system_resources(self, vm_id: str) -> Dict[str, Any]:
        """
        Collect system resource metrics (CPU, RAM).
        
        Args:
            vm_id: VM identifier
        
        Returns:
            Dictionary with system resource metrics
        """
        try:
            resources = {}
            
            # CPU usage
            try:
                exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                    vm_id=vm_id,
                    command="top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\([0-9.]*\)%* id.*/\\1/' | awk '{print 100 - $1}'"
                )
                if exit_code == 0 and stdout.strip():
                    resources['cpu_usage_percent'] = float(stdout.strip())
                else:
                    # Alternative method
                    exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                        vm_id=vm_id,
                        command="cat /proc/loadavg | awk '{print $1}'"
                    )
                    if exit_code == 0:
                        load_avg = float(stdout.strip())
                        exit_code2, cores_out, _ = self.remote_executor.execute_remote_command(
                            vm_id=vm_id,
                            command="nproc"
                        )
                        cores = int(cores_out.strip()) if exit_code2 == 0 else 1
                        resources['cpu_load_avg'] = load_avg
                        resources['cpu_cores'] = cores
                        resources['cpu_usage_percent'] = min(100.0, (load_avg / cores) * 100)
            except Exception as e:
                self.logger.warning(f"Failed to collect CPU metrics: {e}")
                resources['cpu_usage_percent'] = None
            
            # Memory usage
            try:
                exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                    vm_id=vm_id,
                    command="free -m | awk 'NR==2{printf \"%.2f\", $3*100/$2}'"
                )
                if exit_code == 0 and stdout.strip():
                    resources['memory_usage_percent'] = float(stdout.strip())
                else:
                    # Alternative method
                    exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                        vm_id=vm_id,
                        command="free | awk 'NR==2{printf \"%.2f\", $3*100/$2}'"
                    )
                    if exit_code == 0 and stdout.strip():
                        resources['memory_usage_percent'] = float(stdout.strip())
            except Exception as e:
                self.logger.warning(f"Failed to collect memory metrics: {e}")
                resources['memory_usage_percent'] = None
            
            # Memory details
            try:
                exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                    vm_id=vm_id,
                    command="free -m | awk 'NR==2{print $2, $3, $4, $7}'"
                )
                if exit_code == 0:
                    parts = stdout.strip().split()
                    if len(parts) >= 4:
                        resources['memory_total_mb'] = int(parts[0])
                        resources['memory_used_mb'] = int(parts[1])
                        resources['memory_free_mb'] = int(parts[2])
                        resources['memory_available_mb'] = int(parts[3]) if len(parts) > 3 else None
            except Exception as e:
                self.logger.warning(f"Failed to collect memory details: {e}")
            
            return resources
            
        except RemoteExecutorError as e:
            self.logger.error(f"Remote execution error collecting system resources: {e}")
            return {'error': str(e)}
        except Exception as e:
            self.logger.error(f"Unexpected error collecting system resources: {e}")
            return {'error': str(e)}
    
    def _collect_disk_metrics(self, vm_id: str) -> Dict[str, Any]:
        """
        Collect disk usage metrics.
        
        Args:
            vm_id: VM identifier
        
        Returns:
            Dictionary with disk metrics
        """
        try:
            disk_metrics = {}
            
            # Root filesystem usage
            exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                vm_id=vm_id,
                command="df -h / | awk 'NR==2{print $2, $3, $4, $5}'"
            )
            if exit_code == 0:
                parts = stdout.strip().split()
                if len(parts) >= 4:
                    disk_metrics['root_total'] = parts[0]
                    disk_metrics['root_used'] = parts[1]
                    disk_metrics['root_available'] = parts[2]
                    disk_metrics['root_usage_percent'] = int(parts[3].rstrip('%'))
            
            # All filesystems
            exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                vm_id=vm_id,
                command="df -h | awk 'NR>1{print $1, $2, $3, $4, $5, $6}'"
            )
            if exit_code == 0:
                filesystems = []
                for line in stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 6:
                            filesystems.append({
                                'filesystem': parts[0],
                                'total': parts[1],
                                'used': parts[2],
                                'available': parts[3],
                                'usage_percent': int(parts[4].rstrip('%')) if parts[4].endswith('%') else None,
                                'mount_point': parts[5]
                            })
                disk_metrics['filesystems'] = filesystems
            
            return disk_metrics
            
        except Exception as e:
            self.logger.warning(f"Failed to collect disk metrics: {e}")
            return {'error': str(e)}
    
    def _collect_service_status(self, vm_id: str) -> Dict[str, Any]:
        """
        Collect service status metrics.
        
        Args:
            vm_id: VM identifier
        
        Returns:
            Dictionary with service status
        """
        try:
            services = {}
            
            # Get VM role from config
            config = self.remote_executor.config
            vm_config = config.get('vms', {}).get(vm_id, {})
            role = vm_config.get('role', '')
            
            # Check PostgreSQL (VM-02)
            if 'database' in role.lower() or vm_id == 'vm02':
                try:
                    exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                        vm_id=vm_id,
                        command="systemctl is-active postgresql 2>/dev/null || systemctl is-active postgresql@* 2>/dev/null || echo 'inactive'"
                    )
                    services['postgresql'] = {
                        'status': 'active' if exit_code == 0 and 'active' in stdout else 'inactive',
                        'running': 'active' in stdout.lower()
                    }
                except Exception as e:
                    self.logger.warning(f"Failed to check PostgreSQL status: {e}")
                    services['postgresql'] = {'status': 'unknown', 'error': str(e)}
            
            # Check JupyterLab (VM-03)
            if 'jupyter' in role.lower() or vm_id == 'vm03':
                try:
                    exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                        vm_id=vm_id,
                        command="systemctl is-active jupyter 2>/dev/null || pgrep -f jupyter > /dev/null && echo 'active' || echo 'inactive'"
                    )
                    services['jupyterlab'] = {
                        'status': 'active' if exit_code == 0 and 'active' in stdout else 'inactive',
                        'running': 'active' in stdout.lower()
                    }
                except Exception as e:
                    self.logger.warning(f"Failed to check JupyterLab status: {e}")
                    services['jupyterlab'] = {'status': 'unknown', 'error': str(e)}
            
            # Check Docker and n8n (VM-04)
            if 'orchestrator' in role.lower() or 'n8n' in role.lower() or vm_id == 'vm04':
                # Docker
                try:
                    exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                        vm_id=vm_id,
                        command="systemctl is-active docker 2>/dev/null || echo 'inactive'"
                    )
                    services['docker'] = {
                        'status': 'active' if exit_code == 0 and 'active' in stdout else 'inactive',
                        'running': 'active' in stdout.lower()
                    }
                except Exception as e:
                    self.logger.warning(f"Failed to check Docker status: {e}")
                    services['docker'] = {'status': 'unknown', 'error': str(e)}
                
                # n8n container
                try:
                    exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                        vm_id=vm_id,
                        command="docker ps --filter 'name=n8n' --format '{{.Status}}' 2>/dev/null | head -1"
                    )
                    if exit_code == 0 and stdout.strip():
                        services['n8n'] = {
                            'status': 'running' if stdout.strip() else 'stopped',
                            'running': bool(stdout.strip())
                        }
                    else:
                        services['n8n'] = {'status': 'stopped', 'running': False}
                except Exception as e:
                    self.logger.warning(f"Failed to check n8n status: {e}")
                    services['n8n'] = {'status': 'unknown', 'error': str(e)}
            
            return services
            
        except Exception as e:
            self.logger.warning(f"Failed to collect service status: {e}")
            return {'error': str(e)}
    
    def _collect_network_metrics(self, vm_id: str) -> Dict[str, Any]:
        """
        Collect network connectivity metrics.
        
        Args:
            vm_id: VM identifier
        
        Returns:
            Dictionary with network metrics
        """
        try:
            network = {}
            
            # Get VM IP from config
            config = self.remote_executor.config
            vm_config = config.get('vms', {}).get(vm_id, {})
            vm_ip = vm_config.get('ip')
            
            if vm_ip:
                network['ip_address'] = vm_ip
                
                # Check connectivity to other VMs
                connectivity = {}
                for other_vm_id, other_vm_config in config.get('vms', {}).items():
                    if other_vm_id != vm_id and other_vm_config.get('enabled', True):
                        other_ip = other_vm_config.get('ip')
                        if other_ip:
                            # Ping test
                            exit_code, stdout, stderr = self.remote_executor.execute_remote_command(
                                vm_id=vm_id,
                                command=f"ping -c 1 -W 2 {other_ip} > /dev/null 2>&1 && echo 'reachable' || echo 'unreachable'",
                                timeout=5
                            )
                            connectivity[other_vm_id] = {
                                'ip': other_ip,
                                'reachable': 'reachable' in stdout.lower() if exit_code == 0 else False
                            }
                
                network['connectivity'] = connectivity
            
            return network
            
        except Exception as e:
            self.logger.warning(f"Failed to collect network metrics: {e}")
            return {'error': str(e)}

