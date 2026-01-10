"""
Repository Sync Service - Automatic Git repository synchronization.

This module provides services for synchronizing Git repositories across all VMs,
ensuring all hosts have the same version of the codebase.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import yaml

from .remote_executor import RemoteExecutor, RemoteExecutorError
from ..utils.git_manager import GitManager, GitManagerError


class RepoSyncError(Exception):
    """Base exception for repository sync errors."""
    pass


class RepoSyncService:
    """
    Repository synchronization service.
    
    Provides functionality for:
    - Synchronizing repository to all VMs
    - Synchronizing repository to specific VM
    - Checking repository status on VMs
    - Verifying synchronization across VMs
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        remote_executor: Optional[RemoteExecutor] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Repository Sync Service.
        
        Args:
            config_path: Path to config.yml file
            config: Configuration dict (alternative to config_path)
            remote_executor: Optional RemoteExecutor instance (will create if not provided)
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
                raise RepoSyncError(
                    "No configuration provided. Specify config_path or config parameter."
                )
        
        # Get repository configuration
        self.repo_config = self.config.get('repository', {})
        if not self.repo_config:
            raise RepoSyncError("Repository configuration not found in config.yml")
        
        # Initialize remote executor
        if remote_executor:
            self.remote_executor = remote_executor
        else:
            self.remote_executor = RemoteExecutor(
                config=self.config,
                logger=self.logger
            )
        
        # Initialize local Git manager (for VM04 - orchestrator)
        main_repo_path = self.repo_config.get('main_repo_path')
        if main_repo_path:
            try:
                self.local_git = GitManager(main_repo_path, logger=self.logger)
            except GitManagerError as e:
                self.logger.warning(f"Could not initialize local Git manager: {e}")
                self.local_git = None
        else:
            self.local_git = None
        
        self.logger.info("RepoSyncService initialized")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            self.logger.debug(f"Configuration loaded from {config_path}")
            return config
        except Exception as e:
            raise RepoSyncError(f"Failed to load configuration from {config_path}: {e}")
    
    def _get_vm_repo_path(self, vm_id: str) -> str:
        """
        Get repository path for VM.
        
        Args:
            vm_id: VM identifier
        
        Returns:
            Repository path on VM
        """
        vm_repo_paths = self.repo_config.get('vm_repo_paths', {})
        repo_path = vm_repo_paths.get(vm_id)
        
        if not repo_path:
            # Fallback to main_repo_path or default
            repo_path = self.repo_config.get('main_repo_path', '/home/user/th_timmy')
            self.logger.warning(
                f"No repo path configured for {vm_id}, using default: {repo_path}"
            )
        
        return repo_path
    
    def _execute_git_command_on_vm(
        self,
        vm_id: str,
        command: str,
        repo_path: Optional[str] = None
    ) -> Tuple[int, str, str]:
        """
        Execute Git command on remote VM.
        
        Args:
            vm_id: VM identifier
            command: Git command to execute
            repo_path: Repository path on VM (optional)
        
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        if not repo_path:
            repo_path = self._get_vm_repo_path(vm_id)
        
        # Change to repo directory and execute command
        full_command = f"cd {repo_path} && {command}"
        
        return self.remote_executor.execute_remote_command(
            vm_id=vm_id,
            command=full_command,
            timeout=60  # Git operations might take time
        )
    
    def check_repo_status(self, vm_id: str) -> Dict[str, Any]:
        """
        Check repository status on VM.
        
        Args:
            vm_id: VM identifier
        
        Returns:
            Dictionary with repository status:
            - branch: Current branch
            - commit: Current commit hash
            - commit_short: Short commit hash
            - is_clean: Whether working directory is clean
            - has_uncommitted: Whether there are uncommitted changes
            - valid: Whether repository is valid
        """
        try:
            repo_path = self._get_vm_repo_path(vm_id)
            
            # Check if repository exists
            exit_code, stdout, stderr = self._execute_git_command_on_vm(
                vm_id,
                f"test -d {repo_path}/.git && echo 'exists' || echo 'not_found'"
            )
            
            if 'not_found' in stdout:
                return {
                    'valid': False,
                    'error': 'Repository not found',
                    'repo_path': repo_path
                }
            
            # Get current branch
            exit_code, branch_out, branch_err = self._execute_git_command_on_vm(
                vm_id,
                "git rev-parse --abbrev-ref HEAD",
                repo_path
            )
            
            if exit_code != 0:
                return {
                    'valid': False,
                    'error': f'Could not get branch: {branch_err}',
                    'repo_path': repo_path
                }
            
            branch = branch_out.strip()
            
            # Get current commit
            exit_code, commit_out, commit_err = self._execute_git_command_on_vm(
                vm_id,
                "git rev-parse HEAD",
                repo_path
            )
            
            if exit_code != 0:
                return {
                    'valid': False,
                    'error': f'Could not get commit: {commit_err}',
                    'branch': branch,
                    'repo_path': repo_path
                }
            
            commit = commit_out.strip()
            commit_short = commit[:7] if len(commit) >= 7 else commit
            
            # Check if working directory is clean
            exit_code, status_out, status_err = self._execute_git_command_on_vm(
                vm_id,
                "git status --porcelain",
                repo_path
            )
            
            is_clean = len(status_out.strip()) == 0
            has_uncommitted = bool(status_out.strip())
            
            return {
                'valid': True,
                'branch': branch,
                'commit': commit,
                'commit_short': commit_short,
                'is_clean': is_clean,
                'has_uncommitted': has_uncommitted,
                'repo_path': repo_path,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except RemoteExecutorError as e:
            return {
                'valid': False,
                'error': str(e),
                'vm_id': vm_id
            }
        except Exception as e:
            self.logger.error(f"Error checking repo status on {vm_id}: {e}")
            return {
                'valid': False,
                'error': str(e),
                'vm_id': vm_id
            }
    
    def pull_latest_changes(self, vm_id: str, branch: Optional[str] = None) -> Dict[str, Any]:
        """
        Pull latest changes on VM.
        
        Args:
            vm_id: VM identifier
            branch: Branch to pull (default: configured branch or 'main')
        
        Returns:
            Dictionary with pull result:
            - success: Whether pull was successful
            - branch: Branch that was pulled
            - commit_before: Commit before pull
            - commit_after: Commit after pull
            - changed: Whether repository changed
        """
        try:
            if not branch:
                branch = self.repo_config.get('branch', 'main')
            
            repo_path = self._get_vm_repo_path(vm_id)
            
            # Get commit before pull
            status_before = self.check_repo_status(vm_id)
            commit_before = status_before.get('commit', 'unknown')
            
            # Fetch latest
            self.logger.info(f"Fetching latest changes on {vm_id} for branch '{branch}'")
            exit_code, fetch_out, fetch_err = self._execute_git_command_on_vm(
                vm_id,
                f"git fetch origin {branch}",
                repo_path
            )
            
            if exit_code != 0:
                self.logger.warning(f"Git fetch failed on {vm_id}: {fetch_err}")
            
            # Pull changes
            self.logger.info(f"Pulling latest changes on {vm_id} for branch '{branch}'")
            exit_code, pull_out, pull_err = self._execute_git_command_on_vm(
                vm_id,
                f"git pull origin {branch}",
                repo_path
            )
            
            # Get commit after pull
            status_after = self.check_repo_status(vm_id)
            commit_after = status_after.get('commit', 'unknown')
            changed = commit_before != commit_after
            
            if exit_code != 0:
                self.logger.error(f"Git pull failed on {vm_id}: {pull_err}")
                return {
                    'success': False,
                    'vm_id': vm_id,
                    'branch': branch,
                    'commit_before': commit_before,
                    'commit_after': commit_after,
                    'changed': changed,
                    'error': pull_err
                }
            
            if changed:
                self.logger.info(
                    f"Repository updated on {vm_id}: {commit_before[:7]} -> {commit_after[:7]}"
                )
            else:
                self.logger.info(f"Repository on {vm_id} already up to date")
            
            return {
                'success': True,
                'vm_id': vm_id,
                'branch': branch,
                'commit_before': commit_before,
                'commit_after': commit_after,
                'changed': changed,
                'output': pull_out
            }
            
        except RemoteExecutorError as e:
            self.logger.error(f"Error pulling changes on {vm_id}: {e}")
            return {
                'success': False,
                'vm_id': vm_id,
                'error': str(e)
            }
        except Exception as e:
            self.logger.error(f"Unexpected error pulling changes on {vm_id}: {e}")
            return {
                'success': False,
                'vm_id': vm_id,
                'error': str(e)
            }
    
    def sync_repository_to_vm(
        self,
        vm_id: str,
        branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synchronize repository to specific VM.
        
        Args:
            vm_id: VM identifier
            branch: Branch to sync (default: configured branch or 'main')
        
        Returns:
            Dictionary with sync result
        """
        try:
            if not branch:
                branch = self.repo_config.get('branch', 'main')
            
            self.logger.info(f"Synchronizing repository to {vm_id} (branch: {branch})")
            
            # Pull latest changes
            result = self.pull_latest_changes(vm_id, branch)
            
            # Verify sync
            verification = self.verify_sync(vm_id)
            result['verification'] = verification
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error synchronizing repository to {vm_id}: {e}")
            return {
                'success': False,
                'vm_id': vm_id,
                'error': str(e)
            }
    
    def sync_repository_to_all_vms(
        self,
        branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synchronize repository to all enabled VMs.
        
        Args:
            branch: Branch to sync (default: configured branch or 'main')
        
        Returns:
            Dictionary with sync results for all VMs:
            - success: Overall success status
            - results: Dict mapping vm_id to sync result
            - summary: Summary statistics
        """
        try:
            if not branch:
                branch = self.repo_config.get('branch', 'main')
            
            self.logger.info(f"Synchronizing repository to all VMs (branch: {branch})")
            
            # Get all enabled VMs
            vms = self.config.get('vms', {})
            enabled_vms = [
                vm_id for vm_id, vm_config in vms.items()
                if vm_config.get('enabled', True)
            ]
            
            if not enabled_vms:
                raise RepoSyncError("No enabled VMs found in configuration")
            
            results = {}
            successful = 0
            failed = 0
            
            # Sync to each VM
            for vm_id in enabled_vms:
                self.logger.info(f"Synchronizing {vm_id}...")
                result = self.sync_repository_to_vm(vm_id, branch)
                results[vm_id] = result
                
                if result.get('success', False):
                    successful += 1
                else:
                    failed += 1
            
            # Overall verification
            all_synced = self.verify_all_vms_synced()
            
            summary = {
                'total': len(enabled_vms),
                'successful': successful,
                'failed': failed,
                'all_synced': all_synced['synced']
            }
            
            return {
                'success': failed == 0,
                'results': results,
                'summary': summary,
                'verification': all_synced
            }
            
        except Exception as e:
            self.logger.error(f"Error synchronizing repository to all VMs: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_sync(self, vm_id: str) -> Dict[str, Any]:
        """
        Verify synchronization status on VM.
        
        Args:
            vm_id: VM identifier
        
        Returns:
            Dictionary with verification result:
            - synced: Whether VM is synced
            - branch: Current branch
            - commit: Current commit
            - issues: List of issues found
        """
        try:
            status = self.check_repo_status(vm_id)
            
            if not status.get('valid', False):
                return {
                    'synced': False,
                    'vm_id': vm_id,
                    'issues': [status.get('error', 'Unknown error')]
                }
            
            issues = []
            
            # Check for uncommitted changes
            if status.get('has_uncommitted', False):
                issues.append("Has uncommitted changes")
            
            # Check branch matches configured branch
            expected_branch = self.repo_config.get('branch', 'main')
            if status.get('branch') != expected_branch:
                issues.append(
                    f"Branch mismatch: expected '{expected_branch}', got '{status.get('branch')}'"
                )
            
            return {
                'synced': len(issues) == 0,
                'vm_id': vm_id,
                'branch': status.get('branch'),
                'commit': status.get('commit'),
                'commit_short': status.get('commit_short'),
                'issues': issues
            }
            
        except Exception as e:
            self.logger.error(f"Error verifying sync on {vm_id}: {e}")
            return {
                'synced': False,
                'vm_id': vm_id,
                'issues': [str(e)]
            }
    
    def verify_all_vms_synced(self) -> Dict[str, Any]:
        """
        Verify that all VMs are synchronized to the same commit.
        
        Returns:
            Dictionary with verification result:
            - synced: Whether all VMs are synced
            - commit: Common commit (if all synced)
            - vm_statuses: Status for each VM
            - mismatches: List of VMs with different commits
        """
        try:
            # Get all enabled VMs
            vms = self.config.get('vms', {})
            enabled_vms = [
                vm_id for vm_id, vm_config in vms.items()
                if vm_config.get('enabled', True)
            ]
            
            vm_statuses = {}
            commits = {}
            
            # Get status for each VM
            for vm_id in enabled_vms:
                status = self.check_repo_status(vm_id)
                vm_statuses[vm_id] = status
                
                if status.get('valid', False):
                    commit = status.get('commit')
                    if commit:
                        commits[vm_id] = commit
            
            # Check if all commits are the same
            unique_commits = set(commits.values())
            
            if len(unique_commits) == 0:
                return {
                    'synced': False,
                    'vm_statuses': vm_statuses,
                    'issues': ['No valid repositories found']
                }
            
            if len(unique_commits) == 1:
                # All VMs have the same commit
                common_commit = list(unique_commits)[0]
                return {
                    'synced': True,
                    'commit': common_commit,
                    'commit_short': common_commit[:7] if len(common_commit) >= 7 else common_commit,
                    'vm_statuses': vm_statuses
                }
            else:
                # VMs have different commits
                mismatches = []
                commit_groups = {}
                
                for vm_id, commit in commits.items():
                    if commit not in commit_groups:
                        commit_groups[commit] = []
                    commit_groups[commit].append(vm_id)
                
                for commit, vm_list in commit_groups.items():
                    mismatches.append({
                        'commit': commit[:7] if len(commit) >= 7 else commit,
                        'vms': vm_list
                    })
                
                return {
                    'synced': False,
                    'vm_statuses': vm_statuses,
                    'mismatches': mismatches,
                    'issues': [f"Found {len(unique_commits)} different commits across VMs"]
                }
            
        except Exception as e:
            self.logger.error(f"Error verifying all VMs sync: {e}")
            return {
                'synced': False,
                'issues': [str(e)]
            }
    
    def get_local_repo_status(self) -> Optional[Dict[str, Any]]:
        """
        Get local repository status (on VM04 - orchestrator).
        
        Returns:
            Repository status dict or None if local Git manager not available
        """
        if not self.local_git:
            return None
        
        try:
            return self.local_git.get_status()
        except Exception as e:
            self.logger.error(f"Error getting local repo status: {e}")
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

