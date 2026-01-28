"""
Configuration Manager (Step 0.3) – get, update, backup, restore, sync config on VMs.

Uses Step 0.1 (remote_executor): download_file, upload_file, execute_remote_command.
Atomic write on VM: upload to .new then mv. Rollback on failure: restore from backup and re-upload.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from automation_scripts.orchestrators.remote_executor import (
    download_file,
    execute_remote_command,
    upload_file,
)

from .config_backup import create_backup as _create_backup
from .config_backup import list_backups as _list_backups
from .config_backup import restore_backup as _restore_backup
from .config_backup import BackupError
from .config_validator import validate_config

CONFIG_MANAGER_USER = "config_manager"
DEFAULT_TIMEOUT = 60.0


class ConfigManagerError(Exception):
    """Raised on config manager operations failure."""

    pass


def _load_config(config_path: Optional[Union[str, Path]] = None) -> dict:
    path = config_path or Path.cwd() / "configs" / "config.yml"
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _get_remote_path(config: dict, vm_id: str, config_type: str) -> str:
    """Resolve remote file path from config_management.config_paths."""
    cm = config.get("config_management") or {}
    paths = cm.get("config_paths") or {}
    type_paths = paths.get(config_type)
    if not type_paths:
        raise ConfigManagerError(f"No config_paths for config_type={config_type}")
    remote = type_paths.get(vm_id) or type_paths.get("default")
    if not remote:
        raise ConfigManagerError(
            f"No path for config_type={config_type}, vm_id={vm_id} (and no default)"
        )
    return remote.strip()


def _get_schema_path(config: dict, config_type: str, repo_root: Optional[Path] = None) -> Optional[Path]:
    """Resolve schema file path from config_management.config_schemas and schema_dir."""
    cm = config.get("config_management") or {}
    schema_dir = cm.get("schema_dir") or "configs/schemas"
    schemas = cm.get("config_schemas") or {}
    schema_file = schemas.get(config_type)
    if not schema_file:
        return None
    root = repo_root or Path.cwd()
    path = root / schema_dir / schema_file
    return path if path.is_file() else None


def get_config(
    vm_id: str,
    config_type: str,
    *,
    config_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
    raw: bool = False,
    **kwargs: Any,
) -> Union[dict, str]:
    """
    Fetch config file from VM and return as dict (or raw string if raw=True).
    Path from config_management.config_paths.
    """
    cfg = config or _load_config(config_path)
    remote_path = _get_remote_path(cfg, vm_id, config_type)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        local_path = f.name
    try:
        download_file(
            vm_id,
            remote_path,
            local_path,
            CONFIG_MANAGER_USER,
            config_path=config_path,
            config=cfg,
            timeout=kwargs.get("timeout", DEFAULT_TIMEOUT),
            **{k: v for k, v in kwargs.items() if k not in ("timeout",)},
        )
        with open(local_path) as fp:
            content = fp.read()
        if raw:
            return content
        try:
            return yaml.safe_load(content) or {}
        except yaml.YAMLError as e:
            raise ConfigManagerError(f"Failed to parse config YAML: {e}") from e
    except FileNotFoundError as e:
        raise ConfigManagerError(f"Config file not found on VM: {remote_path}") from e
    finally:
        Path(local_path).unlink(missing_ok=True)


def sync_config_to_vm(
    vm_id: str,
    config_type: str,
    config_data: Union[dict, str],
    *,
    config_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
    validate: bool = True,
    backup: bool = False,
    **kwargs: Any,
) -> bool:
    """
    Write config_data to VM (atomic: upload to .new then mv).
    Optionally validate and/or create backup before writing.
    """
    cfg = config or _load_config(config_path)
    remote_path = _get_remote_path(cfg, vm_id, config_type)
    if validate and isinstance(config_data, dict):
        schema_path = _get_schema_path(cfg, config_type)
        if schema_path:
            ok, errs = validate_config(config_data, schema_path)
            if not ok:
                raise ConfigManagerError(f"Validation failed: {errs}")
    if backup and isinstance(config_data, dict):
        try:
            current = get_config(vm_id, config_type, config=cfg, **kwargs)
            if isinstance(current, dict):
                _create_backup(vm_id, config_type, current, config=cfg, **kwargs)
        except (ConfigManagerError, BackupError):
            pass
    if isinstance(config_data, dict):
        content = yaml.dump(config_data, default_flow_style=False, allow_unicode=True)
    else:
        content = config_data if isinstance(config_data, str) else str(config_data)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write(content)
        local_path = f.name
    remote_new = remote_path + ".new"
    try:
        upload_file(
            vm_id,
            local_path,
            remote_new,
            CONFIG_MANAGER_USER,
            config=cfg,
            timeout=kwargs.get("timeout", DEFAULT_TIMEOUT),
        )
        res = execute_remote_command(
            vm_id,
            f"mv -- {_shell_quote(remote_new)} {_shell_quote(remote_path)}",
            CONFIG_MANAGER_USER,
            30.0,
            config=cfg,
        )
        if res.exit_code != 0:
            execute_remote_command(
                vm_id,
                f"rm -f -- {_shell_quote(remote_new)}",
                CONFIG_MANAGER_USER,
                10.0,
                config=cfg,
            )
            raise ConfigManagerError(f"Atomic mv failed: {res.stderr or res.stdout}")
        return True
    finally:
        Path(local_path).unlink(missing_ok=True)


def _shell_quote(s: str) -> str:
    if not s:
        return "''"
    if all(c.isalnum() or c in "/_.-" for c in s):
        return s
    return "'" + s.replace("'", "'\"'\"'") + "'"


def update_config(
    vm_id: str,
    config_type: str,
    config_data: dict,
    *,
    config_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
    validate: bool = True,
    backup: bool = True,
    **kwargs: Any,
) -> Union[bool, dict]:
    """
    Validate config_data, create backup of current config, write new config (atomic).
    On write failure: rollback by restoring from backup and re-uploading.
    Returns True on success; dict with error info on failure.
    """
    cfg = config or _load_config(config_path)
    if validate:
        schema_path = _get_schema_path(cfg, config_type)
        if schema_path:
            ok, errs = validate_config(config_data, schema_path)
            if not ok:
                return {"success": False, "error": "validation_failed", "details": errs}
    backup_id = None
    if backup:
        try:
            current = get_config(vm_id, config_type, config=cfg, **kwargs)
            if isinstance(current, dict):
                backup_id = _create_backup(vm_id, config_type, current, config=cfg, **kwargs)
        except Exception as e:
            if backup_id is None:
                return {"success": False, "error": "backup_failed", "details": str(e)}
    try:
        sync_config_to_vm(
            vm_id,
            config_type,
            config_data,
            config=cfg,
            validate=False,
            backup=False,
            **kwargs,
        )
        return True
    except Exception as e:
        if backup_id:
            try:
                restored = _restore_backup(backup_id, config=cfg, **kwargs)
                sync_config_to_vm(
                    vm_id,
                    config_type,
                    restored,
                    config=cfg,
                    validate=False,
                    backup=False,
                    **kwargs,
                )
            except Exception as rollback_err:
                return {
                    "success": False,
                    "error": "write_failed_rollback_failed",
                    "details": str(e),
                    "rollback_error": str(rollback_err),
                    "backup_id": backup_id,
                }
        return {"success": False, "error": "write_failed", "details": str(e), "backup_id": backup_id}


def backup_config(
    vm_id: str,
    config_type: str,
    *,
    config_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
    **kwargs: Any,
) -> str:
    """Create backup of current config on VM; return backup_id."""
    cfg = config or _load_config(config_path)
    current = get_config(vm_id, config_type, config=cfg, **kwargs)
    if not isinstance(current, dict):
        current = {"_raw": current}
    return _create_backup(vm_id, config_type, current, config=cfg, **kwargs)


def restore_config(
    vm_id: str,
    config_type: str,
    backup_id: str,
    *,
    config_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
    **kwargs: Any,
) -> bool:
    """Restore config on VM from backup_id (atomic write)."""
    cfg = config or _load_config(config_path)
    restored = _restore_backup(backup_id, config=cfg, **kwargs)
    sync_config_to_vm(vm_id, config_type, restored, config=cfg, validate=False, backup=False, **kwargs)
    return True
