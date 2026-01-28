"""Unit tests for repo_sync.git_manager (GitManager, get_commit_hash, pull, fetch, reset)."""

from unittest.mock import patch, MagicMock

import pytest

from automation_scripts.orchestrators.repo_sync.git_manager import (
    GitManager,
    GitOperationError,
)


def test_get_commit_hash_none_when_not_dir(tmp_path):
    """get_commit_hash returns None when repo_path is not a directory."""
    gm = GitManager(tmp_path / "nonexistent")
    assert gm.get_commit_hash() is None


def test_get_commit_hash_returns_hash_when_valid_repo(tmp_path):
    """get_commit_hash returns hash when path is a git repo (mocked subprocess)."""
    (tmp_path / ".git").mkdir()
    with patch(
        "automation_scripts.orchestrators.repo_sync.git_manager._run_git",
        return_value=("abc123def\n", "", 0),
    ):
        gm = GitManager(tmp_path)
        assert gm.get_commit_hash() == "abc123def"


def test_pull_repository_raises_on_failure(tmp_path):
    """pull_repository raises GitOperationError when git pull fails."""
    (tmp_path / ".git").mkdir()
    with patch(
        "automation_scripts.orchestrators.repo_sync.git_manager._run_git",
        return_value=("", "fatal: not a git repository", 128),
    ):
        gm = GitManager(tmp_path)
        with pytest.raises(GitOperationError) as exc:
            gm.pull_repository("main")
        assert "pull" in str(exc.value).lower()
        assert exc.value.returncode == 128


def test_pull_repository_succeeds(tmp_path):
    """pull_repository returns True when git pull succeeds."""
    (tmp_path / ".git").mkdir()
    with patch(
        "automation_scripts.orchestrators.repo_sync.git_manager._run_git",
        return_value=("Already up to date.", "", 0),
    ):
        gm = GitManager(tmp_path)
        assert gm.pull_repository("main") is True


def test_fetch_repository_raises_on_failure(tmp_path):
    """fetch_repository raises GitOperationError when git fetch fails."""
    (tmp_path / ".git").mkdir()
    with patch(
        "automation_scripts.orchestrators.repo_sync.git_manager._run_git",
        return_value=("", "fatal: unable to connect", 128),
    ):
        gm = GitManager(tmp_path)
        with pytest.raises(GitOperationError):
            gm.fetch_repository()


def test_reset_to_commit_raises_on_failure(tmp_path):
    """reset_to_commit raises GitOperationError when git reset fails."""
    (tmp_path / ".git").mkdir()
    with patch(
        "automation_scripts.orchestrators.repo_sync.git_manager._run_git",
        return_value=("", "fatal: invalid ref", 128),
    ):
        gm = GitManager(tmp_path)
        with pytest.raises(GitOperationError) as exc:
            gm.reset_to_commit("abc123")
        assert "reset" in str(exc.value).lower()


def test_reset_to_commit_succeeds(tmp_path):
    """reset_to_commit returns True when git reset --hard succeeds."""
    (tmp_path / ".git").mkdir()
    with patch(
        "automation_scripts.orchestrators.repo_sync.git_manager._run_git",
        return_value=("", "", 0),
    ):
        gm = GitManager(tmp_path)
        assert gm.reset_to_commit("abc123") is True


def test_clone_repository_raises_when_target_non_empty(tmp_path):
    """clone_repository raises when target path exists and is non-empty."""
    (tmp_path / "dest").mkdir()
    (tmp_path / "dest" / "existing").touch()
    gm = GitManager(tmp_path)
    with pytest.raises(GitOperationError) as exc:
        gm.clone_repository("git@example.com/repo.git", tmp_path / "dest", "main")
    assert "non-empty" in str(exc.value).lower() or "Target" in str(exc.value)
