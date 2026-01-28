"""
Repository sync: sync on VM04, push tree to VM01–VM03 via rsync.

Uses GitManager on VM04 only; rsync over SSH; execute_remote_command (Step 0.1) for verification.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

import yaml

from .git_manager import GitManager, GitOperationError
from .secret_scanner import SecretScanResult, scan_repository

# Step 0.1 – use only public API
from automation_scripts.orchestrators.remote_executor import execute_remote_command
from automation_scripts.orchestrators.remote_executor.ssh_key_manager import get_key_base_dir

SYNC_REV_FILE = ".sync_rev"


def _ts_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_config(config_path: Optional[Union[str, Path]] = None) -> dict:
    path = Path(config_path) if config_path else Path.cwd() / "configs" / "config.yml"
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _repository_settings(config: dict) -> dict:
    repo = config.get("repository") or {}
    re_cfg = config.get("remote_execution") or {}
    return {
        "main_repo_path": repo.get("main_repo_path") or "",
        "vm_repo_paths": repo.get("vm_repo_paths") or {},
        "default_branch": repo.get("default_branch", "main"),
        "exclude_dot_git": repo.get("exclude_dot_git", True),
        "rsync_excludes": repo.get("rsync_excludes") or [".git", "__pycache__", "*.pyc", ".vscode", ".DS_Store"],
        "key_storage_path": re_cfg.get("key_storage_path") or repo.get("key_storage_path"),
        "secret_scanning": repo.get("secret_scanning") or {},
        "push_targets": repo.get("push_targets"),  # optional: ["vm01","vm02","vm03"]
    }


def _target_vm_ids(config: dict) -> list[str]:
    """VM IDs we push to (VM01–VM03 only; VM04 is source)."""
    targets = (config.get("repository") or {}).get("push_targets")
    if targets is not None:
        return list(targets)
    vms = config.get("vms") or {}
    return [k for k in sorted(vms.keys()) if k != "vm04" and vms.get(k, {}).get("enabled", True)]


def _get_vm_connection_params(config: dict, vm_id: str) -> dict:
    vms = config.get("vms") or {}
    vm = vms.get(vm_id)
    if not vm:
        raise ValueError(f"vm_id {vm_id} not found in config")
    host = vm.get("ip")
    if not host:
        raise ValueError(f"vm_id {vm_id} has no ip in config")
    return {
        "host": host,
        "port": int(vm.get("ssh_port", 22)),
        "username": vm.get("ssh_user", "thadmin"),
    }


def _get_ssh_key_path(vm_id: str, key_storage_path: Optional[str] = None) -> Optional[str]:
    """Path to SSH private key for vm_id (same convention as Step 0.1)."""
    base = get_key_base_dir(key_storage_path)
    for name in (f"id_ed25519_{vm_id}", f"id_rsa_{vm_id}", f"id_ecdsa_{vm_id}"):
        p = base / name
        if p.is_file():
            return str(p)
    return None


@dataclass
class RepoStatus:
    """Status of repository on a VM (from .sync_rev and VM04 hash)."""

    vm_id: str
    branch: str
    commit_hash: Optional[str]
    is_synced: bool
    last_sync: str
    local_changes: str  # "n/a" for push model (we overwrite)
    error: Optional[str] = None


def _run_rsync(
    source_dir: Path,
    remote_user: str,
    remote_host: str,
    remote_path: str,
    excludes: list[str],
    ssh_key_path: Optional[str] = None,
    ssh_port: int = 22,
    timeout: int = 300,
) -> tuple[bool, str]:
    """Run rsync from source_dir to user@host:path. Returns (success, stderr_or_empty)."""
    source = str(source_dir).rstrip("/") + "/"
    dest = f"{remote_user}@{remote_host}:{remote_path.rstrip('/')}/"
    ssh_cmd_parts = ["ssh", "-o", "ConnectTimeout=15", "-o", "BatchMode=yes", "-p", str(ssh_port)]
    if ssh_key_path:
        ssh_cmd_parts.extend(["-i", ssh_key_path])
    ssh_cmd = " ".join(ssh_cmd_parts)
    args = ["rsync", "-a", "-z", "-h", "--timeout=120", f"--rsh={ssh_cmd}"]
    for ex in excludes:
        args.extend(["--exclude", ex])
    args.extend([source, dest])
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return (r.returncode == 0, r.stderr or "")
    except subprocess.TimeoutExpired:
        return (False, "rsync timed out")
    except FileNotFoundError:
        return (False, "rsync or ssh not found")


def sync_repository_to_vm(
    vm_id: str,
    branch: str = "main",
    force: bool = False,
    *,
    user: str = "sync",
    config_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
    run_secret_scan: bool = True,
    block_on_secrets: bool = True,
) -> RepoStatus:
    """
    Sync repo on VM04, then push tree to the given VM via rsync.

    1) Optional secret scan; if has_secrets and block_on_secrets → return error status.
    2) Git pull (or fetch+reset if force) on VM04.
    3) Write .sync_rev with commit hash, rsync tree to target.
    """
    cfg = config or _load_config(config_path)
    opts = _repository_settings(cfg)
    main_path = Path(opts["main_repo_path"]).expanduser().resolve()
    if not main_path.is_dir():
        return RepoStatus(
            vm_id=vm_id,
            branch=branch,
            commit_hash=None,
            is_synced=False,
            last_sync=_ts_utc(),
            local_changes="n/a",
            error=f"main_repo_path not a directory: {main_path}",
        )
    vm_paths = opts["vm_repo_paths"]
    if vm_id not in vm_paths:
        return RepoStatus(
            vm_id=vm_id,
            branch=branch,
            commit_hash=None,
            is_synced=False,
            last_sync=_ts_utc(),
            local_changes="n/a",
            error=f"vm_id {vm_id} not in repository.vm_repo_paths",
        )
    remote_path = vm_paths[vm_id]
    conn = _get_vm_connection_params(cfg, vm_id)
    key_path = _get_ssh_key_path(vm_id, opts.get("key_storage_path"))

    if run_secret_scan:
        ss_cfg = opts.get("secret_scanning") or {}
        if ss_cfg.get("enabled", True):
            res = scan_repository(
                main_path,
                config_path=ss_cfg.get("config_path"),
                gitleaks_path=ss_cfg.get("tool", "gitleaks"),
            )
            if res.has_secrets and block_on_secrets:
                return RepoStatus(
                    vm_id=vm_id,
                    branch=branch,
                    commit_hash=None,
                    is_synced=False,
                    last_sync=_ts_utc(),
                    local_changes="n/a",
                    error="sync blocked: secrets detected (run_secret_scan=True, block_on_secrets=True)",
                )

    gm = GitManager(main_path)
    if force:
        try:
            gm.fetch_repository()
            ref_hash = gm.get_commit_hash(f"origin/{branch}")
            if not ref_hash:
                raise GitOperationError(f"origin/{branch} not found after fetch", returncode=-1)
            gm.reset_to_commit(ref_hash)
        except GitOperationError:
            pass  # Fallback: use local HEAD if fetch/reset fails (no remote, no network)
    else:
        try:
            gm.pull_repository(branch)
        except GitOperationError:
            pass  # Fallback: use local state if pull fails (no remote, no network, no auth)
    commit_hash = gm.get_commit_hash("HEAD")
    if not commit_hash:
        return RepoStatus(
            vm_id=vm_id,
            branch=branch,
            commit_hash=None,
            is_synced=False,
            last_sync=_ts_utc(),
            local_changes="n/a",
            error="could not get commit hash (not a git repo or invalid state)",
        )

    rev_file = main_path / SYNC_REV_FILE
    try:
        rev_file.write_text(commit_hash + "\n", encoding="utf-8")
    except OSError as e:
        return RepoStatus(
            vm_id=vm_id,
            branch=branch,
            commit_hash=commit_hash,
            is_synced=False,
            last_sync=_ts_utc(),
            local_changes="n/a",
            error=f"could not write {SYNC_REV_FILE}: {e}",
        )

    excludes = list(opts.get("rsync_excludes") or [])
    if opts.get("exclude_dot_git", True) and ".git" not in excludes:
        excludes.append(".git")
    ok, err = _run_rsync(
        main_path,
        conn["username"],
        conn["host"],
        remote_path,
        excludes,
        ssh_key_path=key_path,
        ssh_port=conn["port"],
    )
    if not ok:
        return RepoStatus(
            vm_id=vm_id,
            branch=branch,
            commit_hash=commit_hash,
            is_synced=False,
            last_sync=_ts_utc(),
            local_changes="n/a",
            error=err or "rsync failed",
        )
    return RepoStatus(
        vm_id=vm_id,
        branch=branch,
        commit_hash=commit_hash,
        is_synced=True,
        last_sync=_ts_utc(),
        local_changes="n/a",
    )


def sync_repository_to_all_vms(
    branch: str = "main",
    force: bool = False,
    *,
    user: str = "sync",
    config_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
    run_secret_scan: bool = True,
    block_on_secrets: bool = True,
) -> dict[str, RepoStatus]:
    """Sync on VM04, then push to all target VMs (vm01–vm03). Returns vm_id -> RepoStatus."""
    cfg = config or _load_config(config_path)
    targets = _target_vm_ids(cfg)
    out: dict[str, RepoStatus] = {}
    for vid in targets:
        out[vid] = sync_repository_to_vm(
            vid,
            branch=branch,
            force=force,
            user=user,
            config=cfg,
            run_secret_scan=(run_secret_scan and len(out) == 0),  # scan once before first push
            block_on_secrets=block_on_secrets,
        )
        if out[vid].error and block_on_secrets and run_secret_scan and "secrets detected" in (out[vid].error or ""):
            break
    return out


def check_repo_status(
    vm_id: str,
    *,
    user: str = "sync",
    config_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
) -> RepoStatus:
    """Read .sync_rev on target via execute_remote_command; compare with VM04 hash."""
    cfg = config or _load_config(config_path)
    opts = _repository_settings(cfg)
    main_path = Path(opts["main_repo_path"]).expanduser().resolve()
    vm_paths = opts["vm_repo_paths"]
    if vm_id not in vm_paths:
        return RepoStatus(
            vm_id=vm_id,
            branch=opts.get("default_branch", "main"),
            commit_hash=None,
            is_synced=False,
            last_sync="",
            local_changes="n/a",
            error=f"vm_id {vm_id} not in repository.vm_repo_paths",
        )
    remote_path = vm_paths[vm_id]
    gm = GitManager(main_path)
    expected_hash = gm.get_commit_hash("HEAD")
    try:
        res = execute_remote_command(
            vm_id,
            f"cat {remote_path.rstrip('/')}/{SYNC_REV_FILE} 2>/dev/null || echo ''",
            user,
            15.0,
            config=cfg,
        )
        remote_hash = (res.stdout or "").strip().splitlines()[0].strip() if res.success else None
    except Exception as e:
        return RepoStatus(
            vm_id=vm_id,
            branch=opts.get("default_branch", "main"),
            commit_hash=expected_hash,
            is_synced=False,
            last_sync="",
            local_changes="n/a",
            error=str(e),
        )
    return RepoStatus(
        vm_id=vm_id,
        branch=opts.get("default_branch", "main"),
        commit_hash=remote_hash or None,
        is_synced=bool(remote_hash and expected_hash and remote_hash == expected_hash),
        last_sync="",
        local_changes="n/a",
    )


def verify_sync(
    expected_commit: Optional[str] = None,
    *,
    config_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
    user: str = "sync",
) -> bool:
    """Check that all target VMs have the same commit as VM04 (via .sync_rev)."""
    cfg = config or _load_config(config_path)
    opts = _repository_settings(cfg)
    main_path = Path(opts["main_repo_path"]).expanduser().resolve()
    target_hash = expected_commit
    if target_hash is None:
        gm = GitManager(main_path)
        target_hash = gm.get_commit_hash("HEAD")
    if not target_hash:
        return False
    targets = _target_vm_ids(cfg)
    for vid in targets:
        st = check_repo_status(vid, user=user, config=cfg)
        if not st.is_synced or (st.commit_hash or "") != target_hash:
            return False
    return True
