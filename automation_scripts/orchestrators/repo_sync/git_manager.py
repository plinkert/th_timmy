"""
Git operations on VM04 only – clone, pull, fetch, reset, get_commit_hash.

Auth via SSH or PAT; no plaintext passwords. Raises GitOperationError with stdout/stderr for logging.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


class GitOperationError(Exception):
    """Raised when a Git command fails. Includes stdout/stderr for logging."""

    def __init__(self, message: str, stdout: str = "", stderr: str = "", returncode: int = -1):
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def _run_git(
    repo_path: Path,
    args: list[str],
    timeout: int = 120,
    env: Optional[dict[str, str]] = None,
) -> tuple[str, str, int]:
    """Run git in repo_path; return (stdout, stderr, returncode)."""
    cmd = ["git", "-C", str(repo_path)] + args
    env = dict(env or {})
    # Ensure we don't prompt for credentials in subprocess
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**subprocess.os.environ, **env},
        )
        return (r.stdout or "", r.stderr or "", r.returncode)
    except subprocess.TimeoutExpired as e:
        raise GitOperationError(
            f"Git command timed out: {' '.join(cmd)}",
            stdout=getattr(e, "output", ""),
            stderr="",
            returncode=-1,
        )
    except FileNotFoundError:
        raise GitOperationError("Git not found in PATH", returncode=-1)


class GitManager:
    """
    Wrapper for Git commands on a local repository (VM04).

    Auth: use SSH URLs (git@...) or PAT via GIT_TOKEN / credential helper.
    Do not pass plaintext passwords.
    """

    def __init__(
        self,
        repo_path: str | Path,
        *,
        git_url: Optional[str] = None,
        timeout: int = 120,
    ):
        self.repo_path = Path(repo_path).resolve()
        self.git_url = git_url
        self.timeout = timeout

    def get_commit_hash(self, ref: str = "HEAD") -> Optional[str]:
        """Return commit hash for ref, or None if repo missing/invalid."""
        if not self.repo_path.is_dir():
            return None
        stdout, stderr, code = _run_git(
            self.repo_path,
            ["rev-parse", ref],
            timeout=30,
        )
        if code != 0:
            return None
        return stdout.strip() or None

    def pull_repository(self, branch: str = "main") -> bool:
        """Run git pull origin <branch>. Returns True on success."""
        stdout, stderr, code = _run_git(
            self.repo_path,
            ["pull", "origin", branch],
            timeout=self.timeout,
        )
        if code != 0:
            raise GitOperationError(
                f"git pull origin {branch} failed",
                stdout=stdout,
                stderr=stderr,
                returncode=code,
            )
        return True

    def fetch_repository(self) -> bool:
        """Run git fetch origin. Returns True on success."""
        stdout, stderr, code = _run_git(
            self.repo_path,
            ["fetch", "origin"],
            timeout=self.timeout,
        )
        if code != 0:
            raise GitOperationError(
                "git fetch origin failed",
                stdout=stdout,
                stderr=stderr,
                returncode=code,
            )
        return True

    def reset_to_commit(self, commit_hash: str) -> bool:
        """Run git reset --hard <commit_hash>. Returns True on success."""
        stdout, stderr, code = _run_git(
            self.repo_path,
            ["reset", "--hard", commit_hash],
            timeout=60,
        )
        if code != 0:
            raise GitOperationError(
                f"git reset --hard {commit_hash[:8]}... failed",
                stdout=stdout,
                stderr=stderr,
                returncode=code,
            )
        return True

    def clone_repository(
        self,
        repo_url: str,
        target_path: str | Path,
        branch: str = "main",
    ) -> bool:
        """Clone repo_url into target_path, checkout branch. Returns True on success."""
        target = Path(target_path).resolve()
        if target.exists() and any(target.iterdir()):
            raise GitOperationError(
                f"Target path non-empty: {target}",
                returncode=-1,
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["git", "clone", "--branch", branch, "--single-branch", repo_url, str(target)]
        try:
            r = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(target.parent),
                env={**subprocess.os.environ, "GIT_TERMINAL_PROMPT": "0"},
            )
            if r.returncode != 0:
                raise GitOperationError(
                    f"git clone failed: {repo_url} -> {target}",
                    stdout=r.stdout or "",
                    stderr=r.stderr or "",
                    returncode=r.returncode,
                )
        except subprocess.TimeoutExpired as e:
            raise GitOperationError(
                f"Git clone timed out: {repo_url}",
                stdout=getattr(e, "output", "") or "",
                stderr="",
                returncode=-1,
            )
        except FileNotFoundError:
            raise GitOperationError("Git not found in PATH", returncode=-1)
        return True
