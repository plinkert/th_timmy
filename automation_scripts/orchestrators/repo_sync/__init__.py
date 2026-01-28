"""
Repository Sync Service (Step 0.2) – sync on VM04, push tree to VM01–VM03 via rsync.

Uses git_manager on VM04 only; rsync over SSH to targets; execute_remote_command (Step 0.1)
for verification (.sync_rev). Secret scanning (gitleaks) before sync.
"""

from .git_manager import GitManager, GitOperationError
from .repo_sync import (
    RepoStatus,
    sync_repository_to_vm,
    sync_repository_to_all_vms,
    check_repo_status,
    verify_sync,
)
from .secret_scanner import SecretScanResult, scan_repository

__all__ = [
    "GitManager",
    "GitOperationError",
    "RepoStatus",
    "sync_repository_to_vm",
    "sync_repository_to_all_vms",
    "check_repo_status",
    "verify_sync",
    "SecretScanResult",
    "scan_repository",
]
