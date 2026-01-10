"""
Git Manager - Local Git repository management utilities.

This module provides utilities for managing Git repositories locally,
including status checking, branch operations, and commit verification.
"""

import os
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime


class GitManagerError(Exception):
    """Base exception for Git manager errors."""
    pass


class GitManager:
    """
    Git repository management utilities.
    
    Provides functions for:
    - Checking repository status
    - Getting current branch and commit
    - Pulling latest changes
    - Verifying repository state
    """
    
    def __init__(
        self,
        repo_path: str,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Git Manager.
        
        Args:
            repo_path: Path to Git repository
            logger: Optional logger instance
        """
        self.repo_path = Path(repo_path).expanduser().resolve()
        self.logger = logger or logging.getLogger(__name__)
        
        # Validate repository path
        if not self.repo_path.exists():
            raise GitManagerError(f"Repository path does not exist: {self.repo_path}")
        
        if not self.repo_path.is_dir():
            raise GitManagerError(f"Repository path is not a directory: {self.repo_path}")
        
        # Verify it's a Git repository
        if not (self.repo_path / '.git').exists():
            raise GitManagerError(f"Not a Git repository: {self.repo_path}")
        
        self.logger.debug(f"GitManager initialized for {self.repo_path}")
    
    def _run_git_command(
        self,
        command: List[str],
        timeout: int = 30,
        check: bool = True
    ) -> Tuple[int, str, str]:
        """
        Run Git command in repository.
        
        Args:
            command: Git command as list (e.g., ['status', '--porcelain'])
            timeout: Command timeout in seconds
            check: Whether to raise exception on non-zero exit code
        
        Returns:
            Tuple of (exit_code, stdout, stderr)
        
        Raises:
            GitManagerError: If command fails and check=True
        """
        try:
            git_cmd = ['git', '-C', str(self.repo_path)] + command
            
            self.logger.debug(f"Running Git command: {' '.join(git_cmd)}")
            
            result = subprocess.run(
                git_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.repo_path)
            )
            
            if check and result.returncode != 0:
                raise GitManagerError(
                    f"Git command failed: {' '.join(git_cmd)}\n"
                    f"Exit code: {result.returncode}\n"
                    f"Stderr: {result.stderr}"
                )
            
            return result.returncode, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            raise GitManagerError(f"Git command timed out after {timeout} seconds")
        except Exception as e:
            raise GitManagerError(f"Error running Git command: {e}")
    
    def get_current_branch(self) -> str:
        """
        Get current branch name.
        
        Returns:
            Current branch name
        
        Raises:
            GitManagerError: If command fails
        """
        exit_code, stdout, stderr = self._run_git_command(['rev-parse', '--abbrev-ref', 'HEAD'])
        
        branch = stdout.strip()
        if not branch:
            raise GitManagerError("Could not determine current branch")
        
        return branch
    
    def get_current_commit(self) -> str:
        """
        Get current commit hash.
        
        Returns:
            Current commit hash (full SHA)
        
        Raises:
            GitManagerError: If command fails
        """
        exit_code, stdout, stderr = self._run_git_command(['rev-parse', 'HEAD'])
        
        commit = stdout.strip()
        if not commit:
            raise GitManagerError("Could not determine current commit")
        
        return commit
    
    def get_commit_short(self) -> str:
        """
        Get short commit hash.
        
        Returns:
            Short commit hash (7 characters)
        
        Raises:
            GitManagerError: If command fails
        """
        exit_code, stdout, stderr = self._run_git_command(['rev-parse', '--short', 'HEAD'])
        
        commit = stdout.strip()
        if not commit:
            raise GitManagerError("Could not determine short commit hash")
        
        return commit
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get repository status.
        
        Returns:
            Dictionary with status information:
            - branch: Current branch
            - commit: Current commit hash
            - commit_short: Short commit hash
            - is_clean: Whether working directory is clean
            - has_uncommitted: Whether there are uncommitted changes
            - has_untracked: Whether there are untracked files
            - ahead: Number of commits ahead of remote
            - behind: Number of commits behind remote
        """
        try:
            # Get basic info
            branch = self.get_current_branch()
            commit = self.get_current_commit()
            commit_short = self.get_commit_short()
            
            # Check if working directory is clean
            exit_code, status_output, _ = self._run_git_command(
                ['status', '--porcelain'],
                check=False
            )
            is_clean = len(status_output.strip()) == 0
            has_uncommitted = bool(status_output.strip())
            
            # Check for untracked files
            has_untracked = '??' in status_output
            
            # Check remote tracking
            ahead = 0
            behind = 0
            try:
                exit_code, branch_info, _ = self._run_git_command(
                    ['rev-list', '--left-right', '--count', f'origin/{branch}...HEAD'],
                    check=False
                )
                if exit_code == 0 and branch_info.strip():
                    parts = branch_info.strip().split('\t')
                    if len(parts) == 2:
                        behind = int(parts[0])
                        ahead = int(parts[1])
            except Exception:
                # Remote might not be configured
                pass
            
            return {
                'branch': branch,
                'commit': commit,
                'commit_short': commit_short,
                'is_clean': is_clean,
                'has_uncommitted': has_uncommitted,
                'has_untracked': has_untracked,
                'ahead': ahead,
                'behind': behind,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            raise GitManagerError(f"Failed to get repository status: {e}")
    
    def pull_latest(self, branch: Optional[str] = None) -> Dict[str, Any]:
        """
        Pull latest changes from remote.
        
        Args:
            branch: Branch to pull (default: current branch)
        
        Returns:
            Dictionary with pull result:
            - success: Whether pull was successful
            - branch: Branch that was pulled
            - commit_before: Commit hash before pull
            - commit_after: Commit hash after pull
            - changed: Whether repository changed
            - output: Git pull output
        """
        try:
            # Get commit before pull
            commit_before = self.get_current_commit()
            
            # Determine branch
            if not branch:
                branch = self.get_current_branch()
            
            # Fetch latest
            self.logger.info(f"Fetching latest changes for branch '{branch}'")
            exit_code, fetch_output, fetch_stderr = self._run_git_command(
                ['fetch', 'origin', branch],
                check=False
            )
            
            if exit_code != 0:
                self.logger.warning(f"Git fetch failed: {fetch_stderr}")
            
            # Pull changes
            self.logger.info(f"Pulling latest changes for branch '{branch}'")
            exit_code, pull_output, pull_stderr = self._run_git_command(
                ['pull', 'origin', branch],
                check=False
            )
            
            # Get commit after pull
            commit_after = self.get_current_commit()
            changed = commit_before != commit_after
            
            if exit_code != 0:
                self.logger.error(f"Git pull failed: {pull_stderr}")
                return {
                    'success': False,
                    'branch': branch,
                    'commit_before': commit_before,
                    'commit_after': commit_after,
                    'changed': changed,
                    'output': pull_output,
                    'error': pull_stderr
                }
            
            if changed:
                self.logger.info(
                    f"Repository updated: {commit_before[:7]} -> {commit_after[:7]}"
                )
            else:
                self.logger.info("Repository already up to date")
            
            return {
                'success': True,
                'branch': branch,
                'commit_before': commit_before,
                'commit_after': commit_after,
                'changed': changed,
                'output': pull_output
            }
            
        except Exception as e:
            raise GitManagerError(f"Failed to pull latest changes: {e}")
    
    def checkout_branch(self, branch: str, create: bool = False) -> bool:
        """
        Checkout branch.
        
        Args:
            branch: Branch name
            create: Whether to create branch if it doesn't exist
        
        Returns:
            True if successful
        
        Raises:
            GitManagerError: If checkout fails
        """
        try:
            cmd = ['checkout', branch]
            if create:
                cmd.insert(1, '-b')
            
            exit_code, stdout, stderr = self._run_git_command(cmd)
            
            self.logger.info(f"Checked out branch: {branch}")
            return True
            
        except Exception as e:
            raise GitManagerError(f"Failed to checkout branch '{branch}': {e}")
    
    def verify_repository(self) -> Dict[str, Any]:
        """
        Verify repository integrity and state.
        
        Returns:
            Dictionary with verification results:
            - valid: Whether repository is valid
            - branch: Current branch
            - commit: Current commit
            - issues: List of issues found
        """
        issues = []
        
        try:
            # Check if it's a valid Git repository
            if not (self.repo_path / '.git').exists():
                issues.append("Not a Git repository")
                return {
                    'valid': False,
                    'issues': issues
                }
            
            # Get status
            status = self.get_status()
            
            # Check for uncommitted changes
            if status['has_uncommitted']:
                issues.append("Has uncommitted changes")
            
            # Check if behind remote
            if status['behind'] > 0:
                issues.append(f"Behind remote by {status['behind']} commits")
            
            return {
                'valid': len(issues) == 0,
                'branch': status['branch'],
                'commit': status['commit'],
                'commit_short': status['commit_short'],
                'issues': issues,
                'status': status
            }
            
        except Exception as e:
            issues.append(f"Error verifying repository: {e}")
            return {
                'valid': False,
                'issues': issues
            }
    
    def get_remote_url(self) -> Optional[str]:
        """
        Get remote repository URL.
        
        Returns:
            Remote URL or None if not configured
        """
        try:
            exit_code, stdout, stderr = self._run_git_command(
                ['remote', 'get-url', 'origin'],
                check=False
            )
            
            if exit_code == 0:
                return stdout.strip()
            return None
            
        except Exception:
            return None

