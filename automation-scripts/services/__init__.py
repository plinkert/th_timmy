"""
Remote execution services for VM management.

This module provides services for remote command execution, file transfer,
script execution, repository synchronization, and health monitoring
on virtual machines.
"""

# Try relative imports first, fallback to direct imports if relative imports fail
# This allows the module to work both as a package and when imported directly
try:
    from .remote_executor import RemoteExecutor
    from .ssh_client import SSHClient
    from .health_monitor import HealthMonitor
    from .metrics_collector import MetricsCollector
    from .test_runner import TestRunner
    from .deployment_manager import DeploymentManager
    from .hardening_manager import HardeningManager
    from .playbook_manager import PlaybookManager
    from .ai_service import AIService, AIServiceError
    from .executive_summary_generator import ExecutiveSummaryGenerator, ExecutiveSummaryGeneratorError
except (ImportError, ValueError):
    # Fallback to direct imports if relative imports fail
    from services.remote_executor import RemoteExecutor
    from services.ssh_client import SSHClient
    from services.health_monitor import HealthMonitor
    from services.metrics_collector import MetricsCollector
    from services.test_runner import TestRunner
    from services.deployment_manager import DeploymentManager
    from services.hardening_manager import HardeningManager
    from services.playbook_manager import PlaybookManager
    from services.ai_service import AIService, AIServiceError
    from services.executive_summary_generator import ExecutiveSummaryGenerator, ExecutiveSummaryGeneratorError

# Temporarily disable repo_sync import to avoid import errors in tests
# from .repo_sync import RepoSyncService

__all__ = ['RemoteExecutor', 'SSHClient', 'HealthMonitor', 'MetricsCollector', 'TestRunner', 'DeploymentManager', 'HardeningManager', 'PlaybookManager', 'AIService', 'AIServiceError', 'ExecutiveSummaryGenerator', 'ExecutiveSummaryGeneratorError']  # 'RepoSyncService']

