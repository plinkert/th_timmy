"""
Remote Execution API – execute_remote_command, execute_remote_script, upload_file, download_file.

Uses ssh_client, ssh_key_manager, audit_logger. Validates vm_id from config.
Retry with exponential backoff; SHA256 verification for transfers.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

import yaml

from .audit_logger import log_operation
from .ssh_client import SSHClient
from .ssh_key_manager import get_private_key_for_vm
from .ssh_client import (
    AuthenticationError,
    CommandTimeoutError,
    HostKeyMismatchError,
    SSHConnectionError,
)

CHUNK_SIZE = 1024 * 1024  # 1 MB for large-file reads
LARGE_FILE_THRESHOLD = 100 * 1024 * 1024  # 100 MB


@dataclass
class RemoteExecutionResult:
    """Result of a remote command execution."""

    stdout: str
    stderr: str
    exit_code: int
    execution_time: float
    timestamp: str
    vm_id: str
    command: str
    success: bool = True


def _ts_utc() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_config(config_path: Optional[Union[str, Path]] = None) -> dict:
    """Load config from path. If None, try configs/config.yml from cwd."""
    path = config_path
    if path is None:
        path = Path.cwd() / "configs" / "config.yml"
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _allowed_vm_ids(config: dict) -> list[str]:
    """Return list of allowed vm_ids from config."""
    re_cfg = config.get("remote_execution") or {}
    if "allowed_vm_ids" in re_cfg:
        return list(re_cfg["allowed_vm_ids"])
    vms = config.get("vms") or {}
    return [k for k, v in vms.items() if v.get("enabled", True)]


def _get_vm_connection_params(config: dict, vm_id: str) -> dict:
    """Return host, port, username for vm_id from config."""
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


def _remote_execution_settings(config: dict) -> dict:
    """Return remote_execution section defaults."""
    re_cfg = config.get("remote_execution") or {}
    return {
        "default_timeout": float(re_cfg.get("default_timeout", 30)),
        "default_retry": int(re_cfg.get("default_retry", 3)),
        "key_storage_path": re_cfg.get("key_storage_path"),
        "checksum_algorithm": re_cfg.get("checksum_algorithm", "sha256"),
    }


def _sha256_local(path: Union[str, Path]) -> str:
    """Compute SHA256 hex digest of local file (chunked for large files)."""
    h = hashlib.sha256()
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    with open(path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _shell_quote(s: str) -> str:
    if not s:
        return "''"
    if all(c.isalnum() or c in "/_.-" for c in s):
        return s
    return "'" + s.replace("'", "'\"'\"'") + "'"


def execute_remote_command(
    vm_id: str,
    command: str,
    user: str,
    timeout: float,
    *,
    config_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
    working_directory: Optional[str] = None,
    environment: Optional[dict[str, str]] = None,
    retries: Optional[int] = None,
    **kwargs: Any,
) -> RemoteExecutionResult:
    """
    Execute a single command on the given VM.

    Validates vm_id, loads key, connects with retry, runs command, logs to audit.
    Returns RemoteExecutionResult (stdout, stderr, exit_code, execution_time, ...).
    """
    cfg = config or _load_config(config_path)
    allowed = _allowed_vm_ids(cfg)
    if vm_id not in allowed:
        start = _ts_utc()
        log_operation(user, vm_id, f"command_rejected_invalid_vm_id:{command[:80]}", start, _ts_utc(), "error", extra={"reason": "vm_id not allowed"})
        raise ValueError(f"vm_id {vm_id} not in allowed list: {allowed}")

    params = _get_vm_connection_params(cfg, vm_id)
    opts = _remote_execution_settings(cfg)
    num_retries = retries if retries is not None else opts["default_retry"]
    key_path = opts.get("key_storage_path")

    pkey = get_private_key_for_vm(vm_id, key_storage_path=key_path)
    start_utc = _ts_utc()
    start_time = time.perf_counter()
    last_error: Optional[Exception] = None

    for attempt in range(num_retries):
        try:
            client = SSHClient(
                host=params["host"],
                port=params["port"],
                username=params["username"],
                pkey=pkey,
                connect_timeout=min(30.0, timeout + 5),
                banner_timeout=60.0,
            )
            client.connect()
            try:
                stdout, stderr, exit_code = client.execute(command, timeout=timeout, workdir=working_directory, env=environment)
            finally:
                client.close()
            elapsed = time.perf_counter() - start_time
            end_utc = _ts_utc()
            status = "success" if exit_code == 0 else "error"
            log_operation(user, vm_id, command[:200], start_utc, end_utc, status, exit_code=exit_code, extra={"execution_time_sec": round(elapsed, 3)})
            return RemoteExecutionResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                execution_time=elapsed,
                timestamp=end_utc,
                vm_id=vm_id,
                command=command,
                success=(exit_code == 0),
            )
        except Exception as e:
            last_error = e
            if attempt + 1 < num_retries:
                time.sleep(2 ** attempt)
            else:
                end_utc = _ts_utc()
                log_operation(user, vm_id, command[:200], start_utc, end_utc, "error", extra={"exception": str(e)})
                raise

    raise last_error or RuntimeError("execute_remote_command failed")


def execute_remote_script(
    vm_id: str,
    script_path: str,
    user: str,
    timeout: float,
    *,
    upload_first: bool = False,
    local_script_path: Optional[Union[str, Path]] = None,
    config_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
    working_directory: Optional[str] = None,
    environment: Optional[dict[str, str]] = None,
    retries: Optional[int] = None,
    **kwargs: Any,
) -> RemoteExecutionResult:
    """
    Execute a script on the remote VM.

    If upload_first is True, uploads local_script_path to script_path on the VM first, then runs it.
    Otherwise script_path is the path on the remote host.
    """
    if upload_first and local_script_path:
        upload_file(vm_id, str(local_script_path), script_path, user, config_path=config_path, config=config, **kwargs)
        cmd = f"chmod +x {_shell_quote(script_path)} && {_shell_quote(script_path)}"
    else:
        cmd = _shell_quote(script_path)
    return execute_remote_command(
        vm_id, cmd, user, timeout,
        config_path=config_path, config=config,
        working_directory=working_directory, environment=environment,
        retries=retries, **kwargs,
    )


def upload_file(
    vm_id: str,
    local_path: Union[str, Path],
    remote_path: str,
    user: str,
    *,
    config_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
    timeout: float = 60.0,
    verify_checksum: bool = True,
    retries: Optional[int] = None,
    **kwargs: Any,
) -> None:
    """
    Upload file to the VM. Verifies SHA256 on remote after transfer (if verify_checksum).
    """
    local_path = Path(local_path)
    if not local_path.is_file():
        raise FileNotFoundError(f"Local file not found: {local_path}")

    cfg = config or _load_config(config_path)
    if vm_id not in _allowed_vm_ids(cfg):
        raise ValueError(f"vm_id {vm_id} not allowed")
    params = _get_vm_connection_params(cfg, vm_id)
    opts = _remote_execution_settings(cfg)
    num_retries = retries if retries is not None else opts["default_retry"]
    key_path = opts.get("key_storage_path")

    expected_sha = _sha256_local(local_path)
    pkey = get_private_key_for_vm(vm_id, key_storage_path=key_path)
    start_utc = _ts_utc()
    last_err: Optional[Exception] = None

    for attempt in range(num_retries):
        try:
            client = SSHClient(
                host=params["host"], port=params["port"], username=params["username"],
                pkey=pkey, connect_timeout=30.0, banner_timeout=60.0,
            )
            client.connect()
            try:
                client.upload_file(str(local_path), remote_path, timeout=timeout)
            finally:
                client.close()

            if verify_checksum:
                res = execute_remote_command(
                    vm_id, f"sha256sum -b {_shell_quote(remote_path)} | cut -d' ' -f1",
                    user, timeout=10.0, config=cfg,
                )
                remote_sha = (res.stdout or "").strip().split()[0] if res.stdout else ""
                if remote_sha and remote_sha != expected_sha:
                    log_operation(user, vm_id, f"upload_verify_failed:{remote_path}", start_utc, _ts_utc(), "error", extra={"expected_sha": expected_sha[:16], "remote_sha": remote_sha[:16]})
                    raise ValueError(f"SHA256 mismatch for {remote_path}: expected {expected_sha[:16]}..., got {remote_sha[:16]}...")

            log_operation(user, vm_id, f"upload:{local_path} -> {remote_path}", start_utc, _ts_utc(), "success")
            return
        except Exception as e:
            last_err = e
            if attempt + 1 < num_retries:
                time.sleep(2 ** attempt)
            else:
                log_operation(user, vm_id, f"upload_failed:{remote_path}", start_utc, _ts_utc(), "error", extra={"exception": str(e)})
                raise
    raise last_err or RuntimeError("upload_file failed")


def download_file(
    vm_id: str,
    remote_path: str,
    local_path: Union[str, Path],
    user: str,
    *,
    config_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
    timeout: float = 60.0,
    verify_checksum: bool = True,
    retries: Optional[int] = None,
    **kwargs: Any,
) -> None:
    """
    Download file from the VM. Verifies SHA256 locally after transfer (if verify_checksum).
    """
    local_path = Path(local_path)
    cfg = config or _load_config(config_path)
    if vm_id not in _allowed_vm_ids(cfg):
        raise ValueError(f"vm_id {vm_id} not allowed")
    params = _get_vm_connection_params(cfg, vm_id)
    opts = _remote_execution_settings(cfg)
    num_retries = retries if retries is not None else opts["default_retry"]
    key_path = opts.get("key_storage_path")

    pkey = get_private_key_for_vm(vm_id, key_storage_path=key_path)
    start_utc = _ts_utc()
    last_err: Optional[Exception] = None

    for attempt in range(num_retries):
        try:
            expected_sha = None
            if verify_checksum:
                res = execute_remote_command(
                    vm_id, f"sha256sum -b {_shell_quote(remote_path)} | cut -d' ' -f1",
                    user, timeout=10.0, config=cfg,
                )
                expected_sha = (res.stdout or "").strip().split()[0] if res.stdout else None

            client = SSHClient(
                host=params["host"], port=params["port"], username=params["username"],
                pkey=pkey, connect_timeout=30.0, banner_timeout=60.0,
            )
            client.connect()
            try:
                client.download_file(remote_path, str(local_path), timeout=timeout)
            finally:
                client.close()

            if verify_checksum and expected_sha and local_path.is_file():
                actual_sha = _sha256_local(local_path)
                if actual_sha != expected_sha:
                    log_operation(user, vm_id, f"download_verify_failed:{remote_path}", start_utc, _ts_utc(), "error", extra={"expected_sha": expected_sha[:16], "actual_sha": actual_sha[:16]})
                    raise ValueError(f"SHA256 mismatch for {local_path}: expected {expected_sha[:16]}..., got {actual_sha[:16]}...")

            log_operation(user, vm_id, f"download:{remote_path} -> {local_path}", start_utc, _ts_utc(), "success")
            return
        except Exception as e:
            last_err = e
            if attempt + 1 < num_retries:
                time.sleep(2 ** attempt)
            else:
                log_operation(user, vm_id, f"download_failed:{remote_path}", start_utc, _ts_utc(), "error", extra={"exception": str(e)})
                raise
    raise last_err or RuntimeError("download_file failed")
